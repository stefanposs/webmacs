"""Firmware update management endpoints (core)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from webmacs_backend.dependencies import AdminUser, CurrentUser, DbSession
from webmacs_backend.enums import UpdateStatus
from webmacs_backend.models import FirmwareUpdate
from webmacs_backend.repository import ConflictError, delete_by_public_id, get_or_404, paginate
from webmacs_backend.schemas import (
    FirmwareApplyRequest,
    FirmwareUpdateCreate,
    FirmwareUpdateResponse,
    PaginatedResponse,
    StatusResponse,
    UpdateCheckResponse,
)
from webmacs_backend.services.ota_service import (
    InvalidTransitionError,
    apply_update,
    check_for_updates,
    rollback_update,
    start_update_with_download,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[FirmwareUpdateResponse])
async def list_firmware_updates(
    db: DbSession,
    admin_user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[FirmwareUpdateResponse]:
    """List all firmware updates (admin only)."""
    return await paginate(db, FirmwareUpdate, FirmwareUpdateResponse, page=page, page_size=page_size)


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_firmware_update(
    data: FirmwareUpdateCreate,
    db: DbSession,
    admin_user: AdminUser,
) -> StatusResponse:
    from sqlalchemy import select

    result = await db.execute(select(FirmwareUpdate).where(FirmwareUpdate.version == data.version))
    if result.scalar_one_or_none():
        raise ConflictError("FirmwareUpdate")

    db.add(
        FirmwareUpdate(
            public_id=str(uuid.uuid4()),
            version=data.version,
            changelog=data.changelog,
            user_public_id=admin_user.public_id,
        )
    )
    return StatusResponse(status="success", message="Firmware update successfully registered.")


@router.get("/check", response_model=UpdateCheckResponse)
async def check_updates(
    db: DbSession,
    current_user: CurrentUser,
) -> UpdateCheckResponse:
    """Check if a newer firmware version is available (any authenticated user)."""
    return await check_for_updates(db)


@router.get("/{public_id}", response_model=FirmwareUpdateResponse)
async def get_firmware_update(
    public_id: str,
    db: DbSession,
    admin_user: AdminUser,
) -> FirmwareUpdateResponse:
    """Get a single firmware update by public_id (admin only)."""
    fw = await get_or_404(db, FirmwareUpdate, public_id, entity_name="FirmwareUpdate")
    return FirmwareUpdateResponse.model_validate(fw)


@router.post("/{public_id}/apply", response_model=StatusResponse)
async def apply_firmware_update(
    public_id: str,
    db: DbSession,
    admin_user: AdminUser,
    data: FirmwareApplyRequest | None = None,
) -> StatusResponse:
    """Apply a firmware update (admin only)."""
    fw = await get_or_404(db, FirmwareUpdate, public_id, entity_name="FirmwareUpdate")
    try:
        if data and data.download_url:
            await start_update_with_download(db, fw, data.download_url, expected_hash=data.file_hash_sha256)
            if fw.status == UpdateStatus.failed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=fw.error_message or "Firmware download failed.",
                )
        await apply_update(db, fw)
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    await db.commit()
    return StatusResponse(status="success", message="Firmware update applied successfully.")


@router.post("/{public_id}/rollback", response_model=StatusResponse)
async def rollback_firmware_update(
    public_id: str,
    db: DbSession,
    admin_user: AdminUser,
) -> StatusResponse:
    """Rollback a firmware update (admin only)."""
    fw = await get_or_404(db, FirmwareUpdate, public_id, entity_name="FirmwareUpdate")
    try:
        await rollback_update(db, fw)
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return StatusResponse(status="success", message="Firmware update rolled back successfully.")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_firmware_update(
    public_id: str,
    db: DbSession,
    admin_user: AdminUser,
) -> StatusResponse:
    """Delete a firmware update record (admin only)."""
    return await delete_by_public_id(db, FirmwareUpdate, public_id, entity_name="FirmwareUpdate")
