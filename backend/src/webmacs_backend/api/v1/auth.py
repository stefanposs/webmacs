"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.models import BlacklistToken, User
from webmacs_backend.schemas import LoginRequest, LoginResponse, StatusResponse, UserResponse
from webmacs_backend.security import create_access_token, verify_password

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: DbSession) -> LoginResponse:
    """Authenticate user and return JWT token."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_access_token(user.id)
    return LoginResponse(access_token=token, public_id=user.public_id, username=user.username)


@router.post("/logout", response_model=StatusResponse)
async def logout(
    current_user: CurrentUser,
    db: DbSession,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> StatusResponse:
    """Blacklist the current token."""
    blacklist_entry = BlacklistToken(token=credentials.credentials)
    db.add(blacklist_entry)
    return StatusResponse(status="success", message="Successfully logged out.")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)
