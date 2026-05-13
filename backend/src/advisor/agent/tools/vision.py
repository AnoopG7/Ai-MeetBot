from __future__ import annotations

from livekit.agents.llm import function_tool

from ...core.logging import get_logger
from ...vision.state import state_store

logger = get_logger(__name__)


@function_tool
async def get_visual_context() -> str:
    """Get the user's current visual state — face detection, gaze direction,
    head pose, engagement level, eye presence, smile, mouth movement, nodding,
    and gestures. Call this periodically to stay aware of user engagement."""
    try:
        meta = state_store.get("latest")
        if meta is None:
            return "No visual data — camera may be off."

        parts = [f"Face detected: {meta.face_detected}", f"Faces in view: {meta.face_count}"]
        if meta.face_detected:
            parts.append(f"Gaze: {meta.gaze}")
            parts.append(f"Head pose: {meta.head_pose}")
            parts.append(f"Engagement: {meta.engagement:.2f}")
            parts.append(f"Eyes detected: {meta.eye_count}")
            parts.append(f"Blink rate: {meta.blink_rate:.1f}/s")
            parts.append(f"Smiling: {meta.smiling}")
            parts.append(f"Mouth open: {meta.mouth_open}")
            parts.append(f"Nods: {meta.nod_count}")
            parts.append(f"Looking away: {meta.looking_away_sec:.0f}s")

        note = state_store.get_note("latest")
        if note:
            parts.append(f"ALERT: {note}")

        return " | ".join(parts)
    except Exception:
        logger.exception("visual context failed")
        return "Visual context unavailable."
