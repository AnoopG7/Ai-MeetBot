from __future__ import annotations

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.logging import get_logger
from ...vision.processor import FaceProcessor
from ...vision.state import state_store

logger = get_logger(__name__)

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.websocket("/ws")
async def vision_websocket(ws: WebSocket, participant: str = "unknown") -> None:
    await ws.accept()
    logger.info("vision ws connected", participant=participant)

    processor = FaceProcessor()

    try:
        while True:
            data = await ws.receive_bytes()

            buf = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            h, w = frame.shape[:2]
            if w > 640 or h > 480:
                scale = min(640.0 / w, 480.0 / h, 1.0)
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
                h, w = frame.shape[:2]

            meta = processor.process(frame)

            await state_store.update(participant, meta)
            await state_store.update("latest", meta)

            await ws.send_json({
                "face_detected": meta.face_detected,
                "face_count": meta.face_count,
                "face_x": round(meta.face_x, 3),
                "face_y": round(meta.face_y, 3),
                "face_w": round(meta.face_w, 3),
                "face_h": round(meta.face_h, 3),
                "gaze": meta.gaze,
                "head_pose": meta.head_pose,
                "engagement": meta.engagement,
                "smiling": meta.smiling,
                "mouth_open": meta.mouth_open,
                "left_eye": meta.left_eye,
                "right_eye": meta.right_eye,
                "eye_count": meta.eye_count,
                "blink_rate": meta.blink_rate,
                "nod_count": meta.nod_count,
                "looking_away_sec": round(meta.looking_away_sec, 1),
                "pitch": round(meta.pitch, 1),
                "yaw": round(meta.yaw, 1),
                "roll": round(meta.roll, 1),
                "faces": [
                    {
                        "x": round(f.x, 3),
                        "y": round(f.y, 3),
                        "w": round(f.w, 3),
                        "h": round(f.h, 3),
                        "left_eye": f.left_eye,
                        "right_eye": f.right_eye,
                        "smile": f.smile,
                        "mouth_open": f.mouth_open,
                        "engagement": f.engagement,
                    }
                    for f in meta.faces
                ],
            })
    except WebSocketDisconnect:
        logger.info("vision ws disconnected", participant=participant)
    except Exception:
        logger.exception("vision ws error", participant=participant)
    finally:
        processor.close()
