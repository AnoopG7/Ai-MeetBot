from __future__ import annotations

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from advisor.api.app import app


@pytest.fixture
async def registered_user() -> dict[str, str]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "display_name": "Test User",
                "password": "testpass123",
            },
        )
        if resp.status_code == 409:
            resp = await client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "testpass123"},
            )
        assert resp.status_code in (200, 201), f"auth failed: {resp.text}"
        body = resp.json()
        return {
            "access_token": body["access_token"],
            "user_id": body["user_id"],
            "email": body["email"],
        }


@pytest.mark.asyncio
async def test_auth_register_and_login() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        register_resp = await client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "display_name": "New User",
                "password": "password123",
            },
        )
        if register_resp.status_code == 409:
            register_resp = await client.post(
                "/auth/login",
                json={"email": "newuser@example.com", "password": "password123"},
            )
        assert register_resp.status_code in (200, 201)
        data = register_resp.json()
        assert "access_token" in data
        assert data["email"] == "newuser@example.com"
        assert data["display_name"] == "New User"

        # Fetch profile with token
        profile_resp = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert profile_resp.status_code == 200
        assert profile_resp.json()["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_create_token_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/livekit/token", json={"room": "test-room"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_token_with_auth(registered_user: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/livekit/token",
            json={"room": "test-room"},
            headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        )
        assert resp.status_code == 200, f"token request failed: {resp.text}"
        body = resp.json()
        assert "token" in body
        assert body["room"] == "test-room"
        assert "url" in body

        decoded = jwt.decode(
            body["token"],
            options={"verify_signature": False},
        )
        assert decoded["sub"] == registered_user["user_id"]
        assert decoded["video"]["room"] == "test-room"
        assert decoded["video"]["roomJoin"] is True
