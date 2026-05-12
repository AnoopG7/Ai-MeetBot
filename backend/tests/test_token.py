from __future__ import annotations

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from advisor.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_create_token(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/livekit/token", json={"room": "test-room"})
        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert body["room"] == "test-room"

        decoded = jwt.decode(
            body["token"],
            options={"verify_signature": False},
        )
        assert decoded["sub"] == "user-0.1.0"
        assert decoded["video"]["room"] == "test-room"
        assert decoded["video"]["roomJoin"] is True


@pytest.mark.asyncio
async def test_create_token_custom_identity(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/livekit/token",
            json={"room": "test-room", "identity": "test-user"},
        )
        assert resp.status_code == 200
        body = resp.json()
        decoded = jwt.decode(
            body["token"],
            options={"verify_signature": False},
        )
        assert decoded["sub"] == "test-user"
