import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.audit import EventType, log_event
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _synthetic_user(payload: dict) -> User:
    """Build an in-memory User from JWT claims (used in demo/test mode)."""
    username = payload.get("sub", "demo")
    return User(
        id=uuid.UUID(payload.get("user_id") or str(uuid.uuid4())),
        username=username,
        email=f"{username}@nexus.local",
        hashed_password="",
        role=payload.get("role", "viewer"),
        data_clearance=payload.get("clearance", "internal"),
        is_active=True,
        failed_login_attempts=0,
        locked_until=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = auth.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # In demo/test mode: trust token claims, skip DB lookup
    if settings.DEMO_MODE:
        return _synthetic_user(payload)

    result = await session.execute(select(User).where(User.username == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    ip = request.client.host if request.client else None

    if not user:
        await log_event(session, EventType.LOGIN_FAILED, ip_address=ip,
                        details={"username": body.username, "reason": "user_not_found"})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        await log_event(session, EventType.LOGIN_LOCKED, user_id=user.id, ip_address=ip)
        raise HTTPException(status_code=423, detail="Account locked")

    if not verify_password(body.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        await session.commit()
        await log_event(session, EventType.LOGIN_FAILED, user_id=user.id, ip_address=ip,
                        details={"attempts": user.failed_login_attempts})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.failed_login_attempts = 0
    user.locked_until = None
    await session.commit()

    token_data = {
        "sub": user.username,
        "role": user.role,
        "clearance": user.data_clearance,
        "user_id": str(user.id),
    }
    await log_event(session, EventType.LOGIN_SUCCESS, user_id=user.id, ip_address=ip)
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await session.execute(select(User).where(User.username == payload.get("sub")))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    token_data = {
        "sub": user.username,
        "role": user.role,
        "clearance": user.data_clearance,
        "user_id": str(user.id),
    }
    await log_event(session, EventType.TOKEN_REFRESH, user_id=user.id)
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User))
    return list(result.scalars().all())


@router.post("/users", response_model=UserOut)
async def create_user(
    body: UserCreate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    existing = await session.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        data_clearance=body.data_clearance,
    )
    session.add(user)
    await session.flush()
    await log_event(session, EventType.USER_CREATED, user_id=admin.id,
                    resource_id=str(user.id), details={"username": user.username})
    await session.commit()
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    import uuid
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        user.role = body.role
    if body.data_clearance is not None:
        user.data_clearance = body.data_clearance
    if body.is_active is not None:
        user.is_active = body.is_active

    await session.commit()
    await log_event(session, EventType.USER_UPDATED, user_id=admin.id, resource_id=user_id)
    return user
