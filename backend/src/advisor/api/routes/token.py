from __future__ import annotations

import datetime

from fastapi import APIRouter, HTTPException
from livekit.api import AccessToken, VideoGrants
from pydantic import BaseModel

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/livekit", tags=["livekit"])


class TokenRequest(BaseModel):
    identity: str | None = None
    room: str = "finance-advisor"


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str


@router.post("/token")
async def create_token(req: TokenRequest) -> TokenResponse:
    identity = req.identity or f"user-{settings.app_version}"

    if not settings.livekit_api_key or not settings.livekit_api_secret:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")

    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_ttl(datetime.timedelta(hours=1))
        .with_grants(
            VideoGrants(
                room_join=True,
                room=req.room,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )

    jwt = token.to_jwt()
    logger.info("token issued", identity=identity, room=req.room)

    return TokenResponse(
        token=jwt,
        url=settings.livekit_public_url,
        room=req.room,
    )
