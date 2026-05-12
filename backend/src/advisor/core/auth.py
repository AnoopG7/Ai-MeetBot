from __future__ import annotations

import datetime

import bcrypt
import jwt

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(identity: str) -> str:
    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(seconds=settings.access_token_expire_minutes * 60)
    payload = {
        "sub": identity,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, object] | None:
    try:
        return dict(
            jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        )
    except jwt.PyJWTError:
        return None
