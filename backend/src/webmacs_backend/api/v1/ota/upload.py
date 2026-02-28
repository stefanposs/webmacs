"""OTA upload endpoints (streaming upload to disk)."""

from __future__ import annotations

import os
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, status

from webmacs_backend.dependencies import AdminUser

router = APIRouter()
logger = structlog.get_logger()

UPDATE_DIR = Path(os.environ.get("WEBMACS_UPDATE_DIR", "/updates"))


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_update_bundle(
    file: UploadFile,
    admin_user: AdminUser,
) -> dict:
    """Upload an update bundle (.tar.gz) for OTA deployment (admin only).

    The bundle is saved to the update directory where the self-updater
    service will detect and apply it automatically.
    """
    if not file.filename or not file.filename.endswith(".tar.gz"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .tar.gz update bundle.",
        )

    UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPDATE_DIR / file.filename

    if dest.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bundle '{file.filename}' already exists.",
        )

    # Stream upload to disk (max 500 MB)
    max_size = 500 * 1024 * 1024
    total = 0
    with dest.open("wb") as f:
        while chunk := await file.read(64 * 1024):
            total += len(chunk)
            if total > max_size:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Bundle exceeds maximum allowed size (500 MB).",
                )
            f.write(chunk)

    logger.info("update_bundle_uploaded", filename=file.filename, size_bytes=total)
    return {"status": "success", "message": f"Bundle '{file.filename}' uploaded ({total:,} bytes)."}
