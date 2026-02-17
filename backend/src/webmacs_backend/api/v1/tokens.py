"""API Token management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.models import ApiToken
from webmacs_backend.schemas import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
    PaginatedResponse,
    StatusResponse,
)
from webmacs_backend.security import generate_api_token

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ApiTokenResponse])
async def list_tokens(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[ApiTokenResponse]:
    """List API tokens. Users see their own; admins see all."""
    query = select(ApiToken)
    if not current_user.admin:
        query = query.where(ApiToken.user_id == current_user.id)

    # Count total
    from sqlalchemy import func

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    items = (
        (await db.execute(query.order_by(ApiToken.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    data = [
        ApiTokenResponse(
            public_id=t.public_id,
            name=t.name,
            last_used_at=t.last_used_at,
            expires_at=t.expires_at,
            created_at=t.created_at,
            user_public_id=t.user.public_id,
        )
        for t in items
    ]
    return PaginatedResponse(page=page, page_size=page_size, total=total, data=data)


@router.post("", response_model=ApiTokenCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_token(
    data: ApiTokenCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ApiTokenCreatedResponse:
    """Create a new API token. The plaintext token is returned only once."""
    plaintext, token_hash = generate_api_token()

    token_obj = ApiToken(
        name=data.name,
        token_hash=token_hash,
        user_id=current_user.id,
        expires_at=data.expires_at,
    )
    db.add(token_obj)
    await db.flush()

    return ApiTokenCreatedResponse(
        public_id=token_obj.public_id,
        name=token_obj.name,
        token=plaintext,
        expires_at=token_obj.expires_at,
        created_at=token_obj.created_at,
    )


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_token(
    public_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    """Delete an API token. Users can delete their own; admins can delete any."""
    result = await db.execute(select(ApiToken).where(ApiToken.public_id == public_id))
    token_obj = result.scalar_one_or_none()
    if not token_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API token not found.")

    if not current_user.admin and token_obj.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's token.")

    await db.delete(token_obj)
    return StatusResponse(status="success", message="API token deleted.")
