from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from ...core.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from ...core.database import async_session_factory
from ...core.logging import get_logger
from ...core.models import User

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    display_name: str


class UserProfile(BaseModel):
    user_id: str
    email: str
    display_name: str


async def _extract_token(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header. Use: Bearer <token>",
        )
    return token


async def get_current_user(token: str = Depends(_extract_token)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id_obj = payload.get("sub")
    user_id = str(user_id_obj) if user_id_obj else None
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest) -> AuthResponse:
    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters",
        )
    async with async_session_factory() as session:
        from sqlalchemy import select

        existing = await session.execute(
            select(User).where(User.email == body.email)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = User(
            email=body.email,
            display_name=body.display_name,
            password_hash=hash_password(body.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    token = create_access_token(user.id)
    logger.info("user registered", user_id=user.id, email=user.email)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest) -> AuthResponse:
    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(User.email == body.email)
        )
        user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user.id)
    logger.info("user logged in", user_id=user.id)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


@router.get("/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user)) -> UserProfile:
    return UserProfile(
        user_id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
    )
