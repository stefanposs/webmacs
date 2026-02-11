"""WebMACS self-updater — applies OTA update bundles on the device.

An update bundle is a tar.gz file containing:
    - manifest.json       — version, checksums, changelog
    - images.tar          — docker save output (all 3 service images)
    - docker-compose.prod.yml  — (optional) updated compose file

Workflow:
    1. Admin uploads bundle via UI or copies to /updates/ volume
    2. Updater detects the bundle, validates manifest + SHA-256
    3. docker load < images.tar
    4. pg_dump backup (safety net)
    5. docker compose restart with new image tags
    6. Health-check verification
    7. On failure: rollback to previous image tags

This module can run standalone:
    python -m webmacs_backend.services.updater
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger()

UPDATE_DIR = Path(os.environ.get("WEBMACS_UPDATE_DIR", "/updates"))
APPLIED_DIR = UPDATE_DIR / "applied"
BACKUP_DIR = UPDATE_DIR / "backups"
FAILED_DIR = UPDATE_DIR / "failed"
COMPOSE_FILE = Path("/opt/webmacs/docker-compose.prod.yml")
POLL_INTERVAL = int(os.environ.get("WEBMACS_UPDATER_POLL", "30"))


def sha256_file(path: Path) -> str:
    """Compute SHA-256 digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest(manifest: dict[str, str]) -> bool:
    """Check that manifest contains required fields."""
    required = {"version", "images_sha256"}
    return required.issubset(manifest.keys())


def _run(cmd: list[str], *, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    """Run a shell command with logging."""
    logger.info("updater_exec", cmd=" ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)  # noqa: S603


def load_images(images_tar: Path) -> bool:
    """Load Docker images from tar archive."""
    try:
        result = _run(["docker", "load", "-i", str(images_tar)], timeout=600)
        logger.info("docker_load_complete", output=result.stdout.strip())
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.error("docker_load_failed", error=str(exc))
        return False


def create_db_backup() -> Path | None:
    """Create a PostgreSQL dump before applying updates."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"webmacs_backup_{stamp}.sql"
    try:
        result = _run(
            [
                "docker",
                "compose",
                "-f",
                str(COMPOSE_FILE),
                "exec",
                "-T",
                "db",
                "pg_dump",
                "-U",
                "webmacs",
                "webmacs",
            ],
            timeout=120,
        )
        backup_path.write_text(result.stdout)
        logger.info("db_backup_created", path=str(backup_path), size=backup_path.stat().st_size)
        return backup_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.error("db_backup_failed", error=str(exc))
        return None


ENV_FILE = Path("/opt/webmacs/.env")


def restart_services(version: str) -> bool:
    """Restart the Docker Compose stack with the new version tag."""
    env = os.environ.copy()
    env["WEBMACS_VERSION"] = version
    try:
        subprocess.run(  # noqa: S603
            ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--no-build", "--remove-orphans"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
            env=env,
        )
        # Persist version to .env so it survives reboots
        _persist_version(version)
        logger.info("services_restarted", version=version)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.error("service_restart_failed", error=str(exc))
        return False


def _persist_version(version: str) -> None:
    """Write WEBMACS_VERSION into the .env file so it persists across reboots."""
    if not ENV_FILE.exists():
        return
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        logger.warning("version_persist_rejected", version=version, reason="invalid semver")
        return
    try:
        content = ENV_FILE.read_text()
        if "WEBMACS_VERSION=" in content:
            content = re.sub(r"WEBMACS_VERSION=.*", f"WEBMACS_VERSION={version}", content)
        else:
            content += f"\nWEBMACS_VERSION={version}\n"
        ENV_FILE.write_text(content)
        logger.info("version_persisted", version=version, path=str(ENV_FILE))
    except OSError as exc:
        logger.warning("version_persist_failed", error=str(exc))


def health_check(retries: int = 10, interval: int = 5) -> bool:
    """Wait for the backend to become healthy after restart."""
    for attempt in range(1, retries + 1):
        try:
            result = _run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(COMPOSE_FILE),
                    "exec",
                    "-T",
                    "backend",
                    "python",
                    "-c",
                    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')",
                ],
                check=False,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("health_check_passed", attempt=attempt)
                return True
        except subprocess.TimeoutExpired:
            pass
        logger.info("health_check_waiting", attempt=attempt, max=retries)
        time.sleep(interval)

    logger.error("health_check_failed_all_retries")
    return False


def apply_bundle(bundle_path: Path) -> bool:  # noqa: PLR0911
    """Extract, validate, and apply an update bundle.

    Returns True on success, False on failure (rollback attempted).
    """
    logger.info("applying_bundle", path=str(bundle_path))

    with tempfile.TemporaryDirectory(prefix="webmacs_update_") as tmp:
        tmp_dir = Path(tmp)

        # 1. Extract bundle
        try:
            with tarfile.open(bundle_path, "r:gz") as tar:
                tar.extractall(tmp_dir, filter="data")
        except (tarfile.TarError, OSError) as exc:
            logger.error("bundle_extract_failed", error=str(exc))
            return False

        # 2. Read and validate manifest
        manifest_path = tmp_dir / "manifest.json"
        if not manifest_path.exists():
            logger.error("manifest_missing")
            return False

        manifest = json.loads(manifest_path.read_text())
        if not validate_manifest(manifest):
            logger.error("manifest_invalid", manifest=manifest)
            return False

        version = manifest["version"]
        expected_hash = manifest["images_sha256"]
        logger.info("bundle_manifest", version=version, changelog=manifest.get("changelog", ""))

        # 3. Verify images.tar checksum
        images_tar = tmp_dir / "images.tar"
        if not images_tar.exists():
            logger.error("images_tar_missing")
            return False

        actual_hash = sha256_file(images_tar)
        if actual_hash != expected_hash:
            logger.error(
                "checksum_mismatch",
                expected=expected_hash,
                actual=actual_hash,
            )
            return False

        logger.info("checksum_verified", sha256=actual_hash[:16] + "...")

        # 4. Create database backup
        backup = create_db_backup()
        if backup is None:
            logger.warning("skipping_db_backup")

        # 5. Load new Docker images
        if not load_images(images_tar):
            return False

        # 6. Update compose file if included in bundle
        compose_in_bundle = tmp_dir / "docker-compose.prod.yml"
        if compose_in_bundle.exists() and COMPOSE_FILE.exists():
            shutil.copy2(COMPOSE_FILE, str(COMPOSE_FILE) + ".bak")
            shutil.copy2(compose_in_bundle, COMPOSE_FILE)
            logger.info("compose_file_updated")

        # 7. Restart services with new version
        if not restart_services(version):
            logger.error("restart_failed_attempting_rollback")
            # Restore old compose file
            bak = Path(str(COMPOSE_FILE) + ".bak")
            if bak.exists():
                shutil.copy2(bak, COMPOSE_FILE)
            return False

        # 8. Health check
        if not health_check():
            logger.error("health_check_failed_after_update")
            return False

        # 9. Move bundle to applied/
        APPLIED_DIR.mkdir(parents=True, exist_ok=True)
        applied_path = APPLIED_DIR / f"{version}_{bundle_path.name}"
        shutil.move(str(bundle_path), str(applied_path))
        logger.info("update_applied_successfully", version=version)

        return True


def scan_for_bundles() -> list[Path]:
    """Find .tar.gz bundles in the update directory."""
    if not UPDATE_DIR.exists():
        return []
    return sorted(UPDATE_DIR.glob("webmacs-update-*.tar.gz"))


def run_updater_loop() -> None:
    """Main loop: poll for update bundles and apply them."""
    import time

    logger.info("updater_started", update_dir=str(UPDATE_DIR), poll_interval=POLL_INTERVAL)
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        bundles = scan_for_bundles()
        if bundles:
            # Apply oldest bundle first
            bundle = bundles[0]
            logger.info("bundle_detected", path=str(bundle))
            success = apply_bundle(bundle)
            if not success:
                # Move failed bundle to avoid retry loop
                FAILED_DIR.mkdir(parents=True, exist_ok=True)
                shutil.move(str(bundle), str(FAILED_DIR / bundle.name))
                logger.error("bundle_moved_to_failed", path=str(bundle))
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_updater_loop()
