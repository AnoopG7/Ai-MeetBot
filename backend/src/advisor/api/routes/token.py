from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from livekit.api import AccessToken, LiveKitAPI, VideoGrants
from livekit.protocol import agent_dispatch
from pydantic import BaseModel

from ...core.config import settings
from ...core.logging import get_logger
from ...core.models import User
from ..routes.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/api/livekit", tags=["livekit"])


class TokenRequest(BaseModel):
    room: str = "finance-advisor"


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str


async def _issue_token(identity: str, room: str) -> TokenResponse:
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")

    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_ttl(datetime.timedelta(hours=1))
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )

    jwt = token.to_jwt()

    try:
        api = LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        await api.agent_dispatch.create_dispatch(
            agent_dispatch.CreateAgentDispatchRequest(
                room=room,
                agent_name="",
            )
        )
        await api.aclose()
        logger.info("agent dispatch created", room=room)
    except Exception:
        logger.exception("agent dispatch failed (room may already have one)")

    logger.info("token issued", identity=identity, room=room)

    return TokenResponse(
        token=jwt,
        url=settings.livekit_public_url,
        room=room,
    )


@router.post("/token")
async def create_token(
    req: TokenRequest,
    user: User = Depends(get_current_user),
) -> TokenResponse:
    return await _issue_token(identity=user.id, room=req.room)


@router.post("/token-guest")
async def create_guest_token(req: TokenRequest) -> TokenResponse:
    identity = f"guest-{uuid.uuid4().hex[:12]}"
    return await _issue_token(identity=identity, room=req.room)
