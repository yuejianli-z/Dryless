"""Core blink detection logic for Dryless."""

import os
import shutil
import tempfile
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

import config

_FACE_MODEL_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task"),
    os.path.join(os.getcwd(), "face_landmarker.task"),
]

LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]


def _resolve_model() -> str | None:
    """Resolve the face model path, copying it to temp if the path contains spaces."""
    for path in _FACE_MODEL_CANDIDATES:
        if os.path.exists(path):
            if " " in path:
                temp_model = os.path.join(tempfile.gettempdir(), "face_landmarker.task")
                shutil.copy2(path, temp_model)
                return temp_model
            return path
    return None


_FACE_MODEL = _resolve_model()


def _eye_openness(landmarks, eye_idx):
    points = [landmarks[i] for i in eye_idx]
    top_y = (points[1].y + points[2].y) / 2
    bottom_y = (points[4].y + points[5].y) / 2
    eye_width = abs(points[3].x - points[0].x)
    if eye_width < 1e-6:
        return 0.0
    return (bottom_y - top_y) / eye_width


class BlinkDetector:
    def __init__(self):
        if not _FACE_MODEL:
            raise FileNotFoundError(
                "Face model not found. Expected face_landmarker.task at:\n"
                + "\n".join(f"  {path}" for path in _FACE_MODEL_CANDIDATES)
            )

        options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_FACE_MODEL),
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.3,
            min_face_presence_confidence=0.3,
            min_tracking_confidence=0.3,
            output_face_blendshapes=False,
        )
        self.landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        self.blink_count = 0
        self.face_detected = False
        self.last_blink_time = time.time()
        self._was_open = True
        self.current_openness = 0.0
        self._is_open = True
        self._ratio = None
        self._buf = []
        self._BUF_SIZE = 30
        self._baseline = None
        self._face_left_time: float | None = None

    def process_frame(self, frame):
        """Process one frame and return (frame, blinked, no_blink_sec, debug)."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_img)

        blinked = False
        height, width = frame.shape[:2]

        if result.face_landmarks:
            self.face_detected = True
            landmarks = result.face_landmarks[0]

            self.current_openness = max(
                _eye_openness(landmarks, LEFT_EYE_IDX),
                _eye_openness(landmarks, RIGHT_EYE_IDX),
            )
            self._buf.append(self.current_openness)
            if len(self._buf) > self._BUF_SIZE:
                self._buf.pop(0)
            if len(self._buf) >= 8:
                self._baseline = float(np.percentile(self._buf, 80))

            if self._baseline is not None:
                self._ratio = self.current_openness / self._baseline
                self._is_open = self._ratio >= config.BLINK_RATIO_THRESHOLD
            else:
                self._ratio = None
                self._is_open = True

            if not self._was_open and self._is_open:
                self.blink_count += 1
                self.last_blink_time = time.time()
                blinked = True

            self._was_open = self._is_open

            if self._face_left_time is not None:
                self.last_blink_time = time.time()
                self._face_left_time = None

            color = (74, 161, 78) if self._is_open else (179, 68, 68)
            for eye_idx in [LEFT_EYE_IDX, RIGHT_EYE_IDX]:
                points = np.array(
                    [[int(landmarks[i].x * width), int(landmarks[i].y * height)] for i in eye_idx],
                    dtype=np.int32,
                )
                cv2.polylines(frame, [points], True, color, 1, cv2.LINE_AA)
        else:
            self.face_detected = False
            self._was_open = True
            if self._face_left_time is None:
                self._face_left_time = time.time()

        no_blink_sec = time.time() - self.last_blink_time

        debug = {
            "openness": round(self.current_openness, 3),
            "baseline": round(self._baseline, 3) if self._baseline else 0.0,
            "ratio": round(self._ratio, 3) if self._ratio else None,
            "is_open": self._is_open,
        }
        return frame, blinked, no_blink_sec, debug

    def get_stats(self, no_blink_sec):
        return {
            "face_detected": self.face_detected,
            "no_blink_sec": round(no_blink_sec, 1),
            "blink_count": self.blink_count,
            "alerting": no_blink_sec >= config.NO_BLINK_ALERT_SEC,
        }

    def reset(self):
        self.last_blink_time = time.time()

    def release(self):
        self.landmarker.close()
