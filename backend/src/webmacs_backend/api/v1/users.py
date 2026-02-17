"""User management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from webmacs_backend.dependencies import AdminUser, CurrentUser, DbSession
from webmacs_backend.models import User
from webmacs_backend.repository import ConflictError, delete_by_public_id, get_or_404, paginate
from webmacs_backend.schemas import PaginatedResponse, StatusResponse, UserCreate, UserResponse, UserUpdate
from webmacs_backend.security import hash_password

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: DbSession,
    current_user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[UserResponse]:
    return await paginate(db, User, UserResponse, page=page, page_size=page_size)


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: DbSession, admin_user: AdminUser) -> StatusResponse:
    """Create a new user (admin only)."""
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ConflictError("User")

    db.add(
        User(
            public_id=str(uuid.uuid4()),
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
            role=data.role,
        )
    )
    return StatusResponse(status="success", message="User successfully created.")


@router.get("/{public_id}", response_model=UserResponse)
async def get_user(public_id: str, db: DbSession, current_user: CurrentUser) -> UserResponse:
    user = await get_or_404(db, User, public_id, entity_name="User")
    return UserResponse.model_validate(user)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_user(public_id: str, data: UserUpdate, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    """Update a user. Users may only update themselves; admins can update anyone."""
    if not current_user.admin and current_user.public_id != public_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own profile.")
    user = await get_or_404(db, User, public_id, entity_name="User")
    if data.email is not None:
        user.email = data.email
    if data.username is not None:
        user.username = data.username
    if data.password is not None:
        user.password_hash = hash_password(data.password)
    if data.role is not None:
        # Only admins may change roles
        if not current_user.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change user roles.")
        user.role = data.role
    return StatusResponse(status="success", message="User successfully updated.")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_user(public_id: str, db: DbSession, current_user: AdminUser) -> StatusResponse:
    return await delete_by_public_id(db, User, public_id, entity_name="User")
