from __future__ import annotations

from livekit.agents.llm import function_tool

from ...core.logging import get_logger
from ...vision.state import state_store

logger = get_logger(__name__)


@function_tool
async def get_visual_context() -> str:
    """Get the user's current visual state — face detection, gaze direction,
    head pose, engagement level, eye presence, smile, mouth movement, nodding,
    and gestures. Call this periodically to stay aware of user engagement and
    adapt your tone accordingly."""
    try:
        meta = state_store.get("latest")
        if meta is None:
            return "No visual data available — camera may be off."

        if not meta.face_detected:
            return "No face detected in frame."

        lines = []
        lines.append(f"User is {meta.gaze.replace('_', ' ')}.")
        lines.append(f"Head pose: {meta.head_pose}.")
        lines.append(f"Engagement: {meta.engagement:.0%}.")

        if meta.smiling:
            lines.append("User is smiling — appears positive.")
        if meta.mouth_open:
            lines.append("Mouth is open — user may be speaking or about to speak.")
        if meta.eye_count < 2:
            lines.append(f"Only {meta.eye_count} eye(s) visible — user may be partially turned away.")
        if meta.nod_count > 0:
            lines.append(f"User has nodded {meta.nod_count} time(s) — possible agreement or acknowledgement.")

        lines.append(f"Blink rate: {meta.blink_rate:.1f}/s.")

        if meta.looking_away_sec > 3:
            lines.append(f"ALERT: User has been looking away for {meta.looking_away_sec:.0f} seconds.")

        note = state_store.get_note("latest")
        if note and note != meta.gaze and "looking away" not in note:
            lines.append(f"Note: {note}")

        return " ".join(lines)
    except Exception:
        logger.exception("visual context failed")
        return "Visual context unavailable."
