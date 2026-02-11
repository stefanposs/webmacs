"""OTA (Over-The-Air) update service — version comparison, hash verification, lifecycle."""

from __future__ import annotations

import asyncio
import datetime
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import structlog
from sqlalchemy import select

from webmacs_backend import __version__
from webmacs_backend.config import settings
from webmacs_backend.enums import UpdateStatus
from webmacs_backend.models import FirmwareUpdate
from webmacs_backend.schemas import UpdateCheckResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# ─── GitHub Releases ─────────────────────────────────────────────────────────

GITHUB_API = "https://api.github.com"
_GITHUB_TIMEOUT = 8.0  # seconds


async def check_github_releases() -> dict[str, str | None]:
    """Query GitHub Releases API for the latest release.

    Returns a dict with keys: version, download_url, release_url, error.
    All values default to None on failure.
    """
    repo = settings.github_repo
    if not repo:
        return {"version": None, "download_url": None, "release_url": None, "error": "github_repo not configured"}

    url = f"{GITHUB_API}/repos/{repo}/releases/latest"
    try:
        async with httpx.AsyncClient(timeout=_GITHUB_TIMEOUT) as client:
            resp = await client.get(url, headers={"Accept": "application/vnd.github+json"})

        if resp.status_code == 404:
            logger.info("github_no_releases", repo=repo)
            return {"version": None, "download_url": None, "release_url": None, "error": None}

        if resp.status_code != 200:
            logger.warning("github_api_error", status=resp.status_code, repo=repo)
            return {
                "version": None,
                "download_url": None,
                "release_url": None,
                "error": f"GitHub API returned {resp.status_code}",
            }

        data = resp.json()
        tag = data.get("tag_name", "")
        version = tag.lstrip("v")  # v2.1.0 → 2.1.0
        release_url = data.get("html_url")

        # Find .tar.gz asset
        download_url: str | None = None
        for asset in data.get("assets", []):
            name: str = asset.get("name", "")
            if name.endswith(".tar.gz") and "webmacs-update" in name:
                download_url = asset.get("browser_download_url")
                break

        logger.info("github_latest_release", version=version, has_asset=download_url is not None)
        return {"version": version or None, "download_url": download_url, "release_url": release_url, "error": None}

    except httpx.TimeoutException:
        logger.warning("github_api_timeout", repo=repo)
        return {"version": None, "download_url": None, "release_url": None, "error": "Connection timed out"}
    except httpx.HTTPError as exc:
        logger.warning("github_api_error", error=str(exc), repo=repo)
        return {"version": None, "download_url": None, "release_url": None, "error": str(exc)}


# ─── State machine ───────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[UpdateStatus, set[UpdateStatus]] = {
    UpdateStatus.pending: {UpdateStatus.downloading, UpdateStatus.completed, UpdateStatus.failed},
    UpdateStatus.downloading: {UpdateStatus.verifying, UpdateStatus.failed},
    UpdateStatus.verifying: {UpdateStatus.applying, UpdateStatus.failed},
    UpdateStatus.applying: {UpdateStatus.completed, UpdateStatus.failed},
    UpdateStatus.completed: {UpdateStatus.rolled_back},
    UpdateStatus.failed: {UpdateStatus.pending},
    UpdateStatus.rolled_back: {UpdateStatus.pending},
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, current: UpdateStatus, target: UpdateStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from '{current}' to '{target}'")


def _transition(fw: FirmwareUpdate, target: UpdateStatus) -> None:
    """Validate and apply a state transition."""
    allowed = VALID_TRANSITIONS.get(fw.status, set())
    if target not in allowed:
        raise InvalidTransitionError(fw.status, target)
    fw.status = target


def compare_versions(current: str, candidate: str) -> bool:
    """Return True if *candidate* is strictly newer than *current* (semver)."""

    def _parse(v: str) -> tuple[int, ...]:
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid semver: {v}")
        return tuple(int(p) for p in parts)

    try:
        return _parse(candidate) > _parse(current)
    except (ValueError, TypeError):
        return False


def get_current_version() -> str:
    """Return the running application version from ``__init__.py``."""
    return __version__


async def check_for_updates(db: AsyncSession) -> UpdateCheckResponse:
    """Query firmware records and GitHub Releases for the latest version."""
    current = get_current_version()

    # ── 1. Check local DB for registered firmware records ──────────────
    result = await db.execute(
        select(FirmwareUpdate).where(
            FirmwareUpdate.status.in_([UpdateStatus.pending, UpdateStatus.completed]),
        ),
    )
    candidates = result.scalars().all()

    # Find the highest version that is newer than current
    latest: FirmwareUpdate | None = None
    latest_tuple: tuple[int, ...] = (0, 0, 0)
    for fw in candidates:
        if compare_versions(current, fw.version):
            try:
                fw_tuple = tuple(int(p) for p in fw.version.split("."))
            except (ValueError, TypeError):
                continue
            if fw_tuple > latest_tuple:
                latest = fw
                latest_tuple = fw_tuple

    db_update_available = latest is not None

    # ── 2. Check GitHub Releases ───────────────────────────────────────
    gh = await check_github_releases()
    gh_version = gh["version"]
    gh_update_available = bool(gh_version and compare_versions(current, gh_version))

    # Overall: update available from either source
    update_available = db_update_available or gh_update_available

    # Pick the best latest_version (highest of DB vs GitHub)
    latest_version = latest.version if latest else None
    if gh_version and (not latest_version or compare_versions(latest_version, gh_version)):
        latest_version = gh_version

    return UpdateCheckResponse(
        current_version=current,
        latest_version=latest_version if update_available else None,
        update_available=update_available,
        github_latest_version=gh_version,
        github_download_url=gh["download_url"],
        github_release_url=gh["release_url"],
        github_error=gh["error"],
    )


async def start_update(db: AsyncSession, fw: FirmwareUpdate) -> None:
    """Mark a firmware record as *downloading*.

    .. todo:: Phase 3b — trigger actual firmware download + progress tracking.
    """
    _transition(fw, UpdateStatus.downloading)


def verify_update(file_path: str, expected_hash: str) -> bool:
    """Verify a firmware file against its expected SHA-256 hash (blocking I/O)."""
    path = Path(file_path)
    if not path.is_file():
        return False

    sha256 = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest() == expected_hash


async def apply_update(db: AsyncSession, fw: FirmwareUpdate) -> None:
    """Verify (if applicable) and mark a firmware update as *completed*.

    Placeholder for systemd restart in production.
    """
    if fw.file_path and fw.file_hash_sha256:
        is_valid = await asyncio.to_thread(verify_update, fw.file_path, fw.file_hash_sha256)
        if not is_valid:
            _transition(fw, UpdateStatus.failed)
            fw.error_message = "SHA-256 hash verification failed"
            logger.warning("firmware_hash_verification_failed", firmware_id=fw.public_id)
            return

    _transition(fw, UpdateStatus.completed)
    fw.started_on = fw.started_on or datetime.datetime.now(datetime.UTC)
    fw.completed_on = datetime.datetime.now(datetime.UTC)
    logger.info("firmware_update_applied", firmware_id=fw.public_id, version=fw.version)


async def rollback_update(db: AsyncSession, fw: FirmwareUpdate) -> None:
    """Mark a firmware update as *rolled_back*."""
    _transition(fw, UpdateStatus.rolled_back)
    logger.info("firmware_update_rolled_back", firmware_id=fw.public_id, version=fw.version)
