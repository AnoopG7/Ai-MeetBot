from __future__ import annotations

import time

from .processor import VisualMetadata


class VisualStateStore:
    def __init__(self) -> None:
        self._states: dict[str, VisualMetadata] = {}
        self._expiry: dict[str, float] = {}
        self._notes: dict[str, str | None] = {}
        self._notes_expiry: dict[str, float] = {}
        self._ttl: float = 10.0
        self._note_ttl: float = 30.0

    def update(self, participant: str, meta: VisualMetadata) -> None:
        self._states[participant] = meta
        self._expiry[participant] = time.time() + self._ttl

    def get(self, participant: str) -> VisualMetadata | None:
        meta = self._states.get(participant)
        expiry = self._expiry.get(participant, 0.0)
        if meta is None or time.time() > expiry:
            return None
        return meta

    def store_note(self, participant: str, note: str | None) -> None:
        self._notes[participant] = note
        self._notes_expiry[participant] = time.time() + self._note_ttl

    def get_note(self, participant: str) -> str | None:
        note = self._notes.get(participant)
        expiry = self._notes_expiry.get(participant, 0.0)
        if note is None or time.time() > expiry:
            return None
        return note

    def cleanup(self) -> None:
        now = time.time()
        stale = [k for k, v in self._expiry.items() if now > v]
        for k in stale:
            self._states.pop(k, None)
            self._expiry.pop(k, None)
            self._notes.pop(k, None)
            self._notes_expiry.pop(k, None)


state_store = VisualStateStore()
