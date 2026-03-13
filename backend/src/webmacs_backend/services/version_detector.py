"""Detect installed versions of WebMACS services via the Docker API.

Uses the Docker SDK to inspect running containers and extract the image tag
that was used to start them. Falls back to the Python package ``__version__``
when the Docker socket is unavailable (e.g. in development or tests).

Container name convention (compose project ``webmacs``, or service name):
    webmacs-backend-1  / webmacs_backend_1  / backend
    webmacs-frontend-1 / webmacs_frontend_1 / frontend
    webmacs-controller-1 / webmacs_controller_1 / controller
"""

from __future__ import annotations

import os
from typing import Literal, NamedTuple

import structlog

logger = structlog.get_logger()

# Map service keys → partial container name patterns to search for
_SERVICE_NAME_PATTERNS: dict[str, list[str]] = {
    "backend": ["webmacs-backend", "webmacs_backend", "_backend"],
    "frontend": ["webmacs-frontend", "webmacs_frontend", "_frontend"],
    "controller": ["webmacs-controller", "webmacs_controller", "_controller"],
}

# Docker image references per service (resolved from compose env)
_DEFAULT_IMAGES = {
    "backend": "stefanposs/webmacs-backend",
    "frontend": "stefanposs/webmacs-frontend",
    "controller": "stefanposs/webmacs-controller",
}


ServiceDetectedStatus = Literal["running", "stopped", "error", "unknown"]


class ServiceInfo(NamedTuple):
    installed: str | None
    image: str | None
    status: ServiceDetectedStatus


def _extract_tag(image_ref: str | None) -> str | None:
    """Extract the tag from a Docker image reference, e.g. ``repo/img:2.4.2`` → ``2.4.2``."""
    if not image_ref:
        return None
    if "@" in image_ref:
        return None  # digest-pinned, no meaningful tag
    last_slash = image_ref.rfind("/")
    last_colon = image_ref.rfind(":")
    if last_colon > last_slash:
        tag = image_ref[last_colon + 1 :]
        return tag if tag else None
    return None


def _container_matches(container_name: str, patterns: list[str]) -> bool:
    name_lower = container_name.lower()
    return any(p in name_lower for p in patterns)


def _get_service_info_from_docker(service: str) -> ServiceInfo:
    """Query Docker daemon for the named service's container status + image tag."""
    try:
        import docker  # type: ignore[import-untyped]
        import docker.errors  # type: ignore[import-untyped]
    except ImportError:
        return ServiceInfo(installed=None, image=None, status="unknown")

    try:
        client = docker.from_env(timeout=5)
        patterns = _SERVICE_NAME_PATTERNS.get(service, [])

        matching = [c for c in client.containers.list(all=True) if _container_matches(c.name, patterns)]

        if not matching:
            logger.debug("version_detector_no_container", service=service)
            return ServiceInfo(installed=None, image=_DEFAULT_IMAGES.get(service), status="unknown")

        # Prefer running containers
        running = [c for c in matching if c.status == "running"]
        container = running[0] if running else matching[0]

        image_ref: str = container.image.tags[0] if container.image.tags else ""
        tag = _extract_tag(image_ref)
        status: ServiceDetectedStatus = "running" if container.status == "running" else "stopped"

        return ServiceInfo(installed=tag, image=image_ref or _DEFAULT_IMAGES.get(service), status=status)

    except Exception as exc:
        logger.warning("version_detector_docker_error", service=service, error=str(exc))
        return ServiceInfo(installed=None, image=_DEFAULT_IMAGES.get(service), status="error")


def get_all_service_versions() -> dict[str, ServiceInfo]:
    """Return version info for all three services.

    When the Docker socket is not accessible (dev / CI), falls back to the
    Python package ``__version__`` for the backend and ``None`` for others.
    """
    from webmacs_backend import __version__ as backend_version

    docker_available = os.path.exists("/var/run/docker.sock")
    env_version = os.environ.get("WEBMACS_VERSION") or None

    if docker_available:
        result: dict[str, ServiceInfo] = {}
        for svc in ("backend", "frontend", "controller"):
            info = _get_service_info_from_docker(svc)
            installed = info.installed
            # Fallback: if Docker found nothing, use package __version__ for backend
            # or WEBMACS_VERSION env var for all services
            if installed is None:
                if svc == "backend":
                    installed = backend_version
                elif env_version:
                    installed = env_version
            result[svc] = ServiceInfo(
                installed=installed,
                image=info.image,
                status=info.status,
            )
        return result

    # Dev / no Docker socket — return stubs
    return {
        "backend": ServiceInfo(
            installed=backend_version,
            image=_DEFAULT_IMAGES["backend"],
            status="unknown",
        ),
        "frontend": ServiceInfo(installed=None, image=_DEFAULT_IMAGES["frontend"], status="unknown"),
        "controller": ServiceInfo(installed=None, image=_DEFAULT_IMAGES["controller"], status="unknown"),
    }
