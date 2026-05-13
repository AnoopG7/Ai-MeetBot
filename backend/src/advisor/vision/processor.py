from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

import cv2
import numpy as np

from ..core.logging import get_logger

logger = get_logger(__name__)

EYE_MIN_SIZE = (20, 20)
SMILE_MIN_SIZE = (30, 30)
FACE_MIN_SIZE = (80, 80)
NOD_WINDOW = 20
NOD_THRESHOLD = 3.5


@dataclass
class FaceInfo:
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    left_eye: bool = False
    right_eye: bool = False
    smile: bool = False
    mouth_open: bool = False
    engagement: float = 0.5


@dataclass
class VisualMetadata:
    face_detected: bool = False
    face_count: int = 0
    gaze: str = "unknown"
    head_pose: str = "centered"
    gesture: str = "still"
    engagement: float = 0.0
    smiling: bool = False
    mouth_open: bool = False
    left_eye: bool = False
    right_eye: bool = False
    eye_count: int = 0
    blink_rate: float = 0.0
    nod_count: int = 0
    looking_away_sec: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    timestamp: float = 0.0
    face_x: float = 0.5
    face_y: float = 0.5
    face_w: float = 0.0
    face_h: float = 0.0
    faces: list[FaceInfo] = field(default_factory=list)


class FaceProcessor:
    def __init__(self, history_sec: float = 4.0) -> None:
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._alt_face = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
        )
        self._left_eye = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_lefteye_2splits.xml"
        )
        self._right_eye = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_righteye_2splits.xml"
        )
        self._smile = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_smile.xml"
        )

        self._history: deque[VisualMetadata] = deque()
        self._history_sec = history_sec
        self._nod_deque: deque[float] = deque(maxlen=NOD_WINDOW)
        self._nod_count = 0
        self._nod_up = False
        self._nod_down = False
        self._looking_away_start: float | None = None
        self._blink_events = 0
        self._blink_timer = time.monotonic()
        self._left_eye_history: deque[bool] = deque(maxlen=8)
        self._right_eye_history: deque[bool] = deque(maxlen=8)
        self._blink_debounce: float = 0.0

    def close(self) -> None:
        pass

    def process(self, frame: np.ndarray) -> VisualMetadata:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        now = time.time()
        meta = VisualMetadata(timestamp=now)

        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.08, minNeighbors=4, minSize=FACE_MIN_SIZE
        )
        if len(faces) == 0:
            faces = self._alt_face.detectMultiScale(
                gray, scaleFactor=1.08, minNeighbors=4, minSize=FACE_MIN_SIZE
            )

        if len(faces) == 0:
            return self._no_face(meta, now)

        meta.face_detected = True
        meta.face_count = len(faces)

        all_faces: list[FaceInfo] = []
        total_eng = 0.0
        primary = faces[0]
        primary_area = primary[2] * primary[3]
        for fx, fy, fw, fh in faces:
            area = fw * fh
            if area > primary_area:
                primary = (fx, fy, fw, fh)
                primary_area = area

        for fx, fy, fw, fh in faces:
            fi = self._process_single_face(gray, fx, fy, fw, fh, w, h)
            all_faces.append(fi)
            total_eng += fi.engagement

        meta.faces = all_faces
        meta.engagement = round(total_eng / len(faces), 2)

        pf = all_faces[0]
        meta.face_x = pf.x
        meta.face_y = pf.y
        meta.face_w = pf.w
        meta.face_h = pf.h
        meta.left_eye = pf.left_eye
        meta.right_eye = pf.right_eye
        meta.eye_count = (1 if pf.left_eye else 0) + (1 if pf.right_eye else 0)
        meta.smiling = pf.smile
        meta.mouth_open = pf.mouth_open

        yaw = (pf.x - 0.5) * 60.0
        pitch = (pf.y - 0.5) * 60.0
        meta.yaw = round(yaw, 1)
        meta.pitch = round(pitch, 1)

        meta.head_pose = "centered"
        if abs(yaw) > 25:
            meta.head_pose = "looking_left" if yaw > 0 else "looking_right"
        elif abs(yaw) > 12:
            meta.head_pose = "turned"
        if abs(pitch) > 20:
            meta.head_pose = "looking_down" if pitch > 0 else "looking_up"

        if abs(yaw) > 30:
            meta.gaze = "away"
        elif abs(yaw) > 15:
            meta.gaze = "side"
        else:
            meta.gaze = "at_camera"

        self._track_blinks(pf.left_eye, pf.right_eye)
        elapsed = time.monotonic() - self._blink_timer
        meta.blink_rate = round(self._blink_events / elapsed, 2) if elapsed > 0 else 0.0

        self._nod_deque.append(pf.y)
        self._detect_nod()
        meta.nod_count = self._nod_count

        self._looking_away_start = None
        self._prune(now)
        self._history.append(meta)
        return meta

    def _no_face(self, meta: VisualMetadata, now: float) -> VisualMetadata:
        meta.face_detected = False
        meta.gaze = "away"
        meta.head_pose = "away"
        meta.engagement = 0.0
        if self._looking_away_start is None:
            self._looking_away_start = now
        meta.looking_away_sec = now - self._looking_away_start if self._looking_away_start else 0.0
        self._history.append(meta)
        return meta

    def _process_single_face(
        self, gray: np.ndarray, fx: int, fy: int, fw: int, fh: int,
        frame_w: int, frame_h: int,
    ) -> FaceInfo:
        fi = FaceInfo()
        fi.x = (fx + fw / 2) / frame_w
        fi.y = (fy + fh / 2) / frame_h
        fi.w = fw / frame_w
        fi.h = fh / frame_h

        face_roi = gray[fy:fy + fh, fx:fx + fw]
        roi_h, roi_w = face_roi.shape[:2]

        eye_top = int(roi_h * 0.05)
        eye_bot = int(roi_h * 0.5)
        eye_left = int(roi_w * 0.05)
        eye_right = int(roi_w * 0.95)
        if eye_bot > eye_top and eye_right > eye_left:
            eye_roi = face_roi[eye_top:eye_bot, eye_left:eye_right]
            eh, ew = eye_roi.shape[:2]
            if eh > 0 and ew > 0:
                le = self._left_eye.detectMultiScale(
                    eye_roi, scaleFactor=1.05, minNeighbors=4, minSize=EYE_MIN_SIZE
                )
                re = self._right_eye.detectMultiScale(
                    eye_roi, scaleFactor=1.05, minNeighbors=4, minSize=EYE_MIN_SIZE
                )
                fi.left_eye = len(le) > 0
                fi.right_eye = len(re) > 0

        mouth_top = int(roi_h * 0.55)
        mouth_bot = int(roi_h * 0.9)
        mouth_left = int(roi_w * 0.2)
        mouth_right = int(roi_w * 0.8)
        if mouth_bot > mouth_top and mouth_right > mouth_left:
            mouth_roi = face_roi[mouth_top:mouth_bot, mouth_left:mouth_right]
            mh, mw = mouth_roi.shape[:2]
            if mh > 0 and mw > 0:
                smiles = self._smile.detectMultiScale(
                    mouth_roi, scaleFactor=1.15, minNeighbors=8, minSize=SMILE_MIN_SIZE
                )
                fi.smile = len(smiles) > 0

                variance = float(np.var(mouth_roi))
                fi.mouth_open = variance > 350.0

        fi.engagement = self._single_engagement(fi)
        return fi

    def _track_blinks(self, left_ok: bool, right_ok: bool) -> None:
        self._left_eye_history.append(left_ok)
        self._right_eye_history.append(right_ok)

        if len(self._left_eye_history) < 6:
            return

        now = time.monotonic()
        if now - self._blink_debounce < 0.15:
            return

        left_recent = list(self._left_eye_history)
        right_recent = list(self._right_eye_history)

        left_blink = left_recent[-1] is False and left_recent[-2] is False and left_recent[-3] is True
        right_blink = right_recent[-1] is False and right_recent[-2] is False and right_recent[-3] is True

        if left_blink or right_blink:
            self._blink_events += 1
            self._blink_debounce = now

    def _detect_nod(self) -> None:
        if len(self._nod_deque) < 12:
            return
        recent = list(self._nod_deque)
        mid = len(recent) // 2
        first_half = recent[:mid]
        second_half = recent[mid:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        delta = abs(avg_second - avg_first) * 100
        if delta > NOD_THRESHOLD:
            self._nod_count += 1
            self._nod_deque.clear()

    def _single_engagement(self, fi: FaceInfo) -> float:
        score = 0.5
        if fi.left_eye and fi.right_eye:
            score += 0.25
        elif fi.left_eye or fi.right_eye:
            score += 0.1
        if fi.smile:
            score += 0.15
        face_size = fi.w * fi.h
        if face_size > 0.08:
            score += 0.1
        elif face_size < 0.02:
            score -= 0.15
        return round(max(0.0, min(1.0, score)), 2)

    def _prune(self, now: float) -> None:
        while self._history and now - self._history[0].timestamp > self._history_sec:
            self._history.popleft()
