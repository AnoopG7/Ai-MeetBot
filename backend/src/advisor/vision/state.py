from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict

import redis

from ..core.config import settings
from ..core.logging import get_logger
from .processor import FaceInfo, VisualMetadata

logger = get_logger(__name__)

_STATE_TTL = 10
_NOTE_TTL = 30


class VisualStateStore:
    def __init__(self) -> None:
        self._sync_redis: redis.Redis | None = None
        self._redis_ok = False
        self._local_states: dict[str, VisualMetadata] = {}
        self._local_expiry: dict[str, float] = {}
        self._local_notes: dict[str, str | None] = {}
        self._local_notes_expiry: dict[str, float] = {}

    def _get_sync_redis(self) -> redis.Redis | None:
        if self._sync_redis is None:
            try:
                self._sync_redis = redis.Redis.from_url(settings.redis_url)
                self._sync_redis.ping()
                self._redis_ok = True
                logger.info("visual store connected to redis at %s", settings.redis_url)
            except Exception as exc:
                logger.warning("redis unavailable (%s), using local store", exc)
                self._sync_redis = None
                self._redis_ok = False
        return self._sync_redis if self._redis_ok else None

    async def update(self, participant: str, meta: VisualMetadata) -> None:
        data = asdict(meta)
        data["faces"] = [asdict(f) for f in meta.faces]
        payload = json.dumps(data, default=str)
        self._local_states[participant] = meta
        self._local_expiry[participant] = time.time() + _STATE_TTL
        r = self._get_sync_redis()
        if r is None:
            return
        try:
            await asyncio.to_thread(r.setex, f"vision:state:{participant}", _STATE_TTL, payload)
        except Exception:
            logger.debug("redis write failed")

    async def get(self, participant: str) -> VisualMetadata | None:
        r = self._get_sync_redis()
        if r is not None:
            try:
                raw = await asyncio.to_thread(r.get, f"vision:state:{participant}")
                if raw is not None:
                    self._unpack(raw, participant)
                    return self._local_states.get(participant)
            except Exception:
                logger.debug("redis read failed")
        meta = self._local_states.get(participant)
        expiry = self._local_expiry.get(participant, 0.0)
        if meta is None or time.time() > expiry:
            return None
        return meta

    def _unpack(self, raw: bytes, participant: str) -> None:
        try:
            data = json.loads(raw)
            faces_raw = data.pop("faces", [])
            faces = [FaceInfo(**f) for f in faces_raw]
            meta = VisualMetadata(**data)
            meta.faces = faces
            self._local_states[participant] = meta
            self._local_expiry[participant] = time.time() + _STATE_TTL
        except Exception:
            logger.warning("failed to unpack visual state")

    async def store_note(self, participant: str, note: str | None) -> None:
        self._local_notes[participant] = note
        self._local_notes_expiry[participant] = time.time() + _NOTE_TTL
        r = self._get_sync_redis()
        if r is None:
            return
        try:
            key = f"vision:note:{participant}"
            if note is None:
                await asyncio.to_thread(r.delete, key)
            else:
                await asyncio.to_thread(r.setex, key, _NOTE_TTL, note)
        except Exception:
            pass

    async def get_note(self, participant: str) -> str | None:
        r = self._get_sync_redis()
        if r is not None:
            try:
                raw = await asyncio.to_thread(r.get, f"vision:note:{participant}")
                if raw is not None:
                    val = raw.decode()
                    self._local_notes[participant] = val
                    self._local_notes_expiry[participant] = time.time() + _NOTE_TTL
                    return val
            except Exception:
                pass
        note = self._local_notes.get(participant)
        expiry = self._local_notes_expiry.get(participant, 0.0)
        if note is None or time.time() > expiry:
            return None
        return note

    async def cleanup(self) -> None:
        self._local_states.clear()
        self._local_expiry.clear()
        self._local_notes.clear()
        self._local_notes_expiry.clear()
        if self._sync_redis:
            try:
                await asyncio.to_thread(self._sync_redis.close)
            except Exception:
                pass
            self._sync_redis = None
            self._redis_ok = False


state_store = VisualStateStore()
