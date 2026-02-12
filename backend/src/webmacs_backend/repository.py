"""Generic async repository — eliminates CRUD boilerplate across routers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError

from webmacs_backend.database import Base
from webmacs_backend.schemas import PaginatedResponse, StatusResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ─── Domain Errors ───────────────────────────────────────────────────────────


class NotFoundError(HTTPException):
    """404 for missing entities."""

    def __init__(self, entity_name: str, public_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} '{public_id}' not found.",
        )


class ConflictError(HTTPException):
    """409 for duplicate entities."""

    def __init__(self, entity_name: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{entity_name} already exists.",
        )


# ─── Generic Operations ─────────────────────────────────────────────────────


MAX_PAGE_SIZE = 100


async def paginate[M: Base, S: BaseModel](
    db: AsyncSession,
    model: type[M],
    schema: type[S],
    *,
    page: int = 1,
    page_size: int = 25,
    base_query: Select[Any] | None = None,
) -> PaginatedResponse[S]:
    """Generic paginated list query."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    query = base_query if base_query is not None else select(model)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        data=[schema.model_validate(row) for row in rows],
    )


async def get_or_404[M: Base](
    db: AsyncSession,
    model: type[M],
    public_id: str,
    *,
    entity_name: str = "Resource",
) -> M:
    """Fetch by public_id or raise 404."""
    result = await db.execute(select(model).where(model.public_id == public_id))  # type: ignore[attr-defined]
    entity = result.scalar_one_or_none()
    if not entity:
        raise NotFoundError(entity_name, public_id)
    return entity


async def delete_by_public_id[M: Base](
    db: AsyncSession,
    model: type[M],
    public_id: str,
    *,
    entity_name: str = "Resource",
) -> StatusResponse:
    """Delete by public_id or raise 404."""
    entity = await get_or_404(db, model, public_id, entity_name=entity_name)
    await db.delete(entity)
    return StatusResponse(status="success", message=f"{entity_name} successfully deleted.")


async def update_from_schema[M: Base](
    db: AsyncSession,
    model: type[M],
    public_id: str,
    data: BaseModel,
    *,
    entity_name: str = "Resource",
) -> StatusResponse:
    """Partial update using model_dump(exclude_unset=True)."""
    entity = await get_or_404(db, model, public_id, entity_name=entity_name)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entity, field, value)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(entity_name) from None
    return StatusResponse(status="success", message=f"{entity_name} successfully updated.")
