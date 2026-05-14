# gesture_detector.py — MediaPipe hand-tracking wrapper + gesture classification
# Uses MediaPipe Tasks API (compatible with mediapipe >= 0.10)

import os
import math
import time
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mpPython
from mediapipe.tasks.python import vision as mpVision
import config

# MediaPipe landmark indices
TIP_IDS  = [4, 8, 12, 16, 20]   # thumb, index, middle, ring, pinky tips
BASE_IDS = [2, 5,  9, 13, 17]   # MCP / IP joints (used for thumb horizontal check)
PIP_IDS  = [3, 6, 10, 14, 18]   # thumb-IP, index-PIP, middle-PIP, ring-PIP, pinky-PIP

# Hand skeleton connections (hardcoded — mp.solutions removed in 0.10+)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # Index
    (5, 9), (9, 10), (10, 11), (11, 12),     # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # Pinky
    (0, 17),                                  # Palm base
]

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


class GestureDetector:
    def __init__(self, maxHands=1, detectionConfidence=0.75, trackingConfidence=0.75):
        if not os.path.exists(MODEL_PATH):
            print("[INFO] Downloading hand landmark model (~9 MB) ...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("[INFO] Model downloaded.")

        baseOptions = mpPython.BaseOptions(model_asset_path=MODEL_PATH)
        options = mpVision.HandLandmarkerOptions(
            base_options=baseOptions,
            running_mode=mpVision.RunningMode.VIDEO,   # temporal tracking between frames
            num_hands=maxHands,
            min_hand_detection_confidence=detectionConfidence,
            min_hand_presence_confidence=detectionConfidence,
            min_tracking_confidence=trackingConfidence,
        )
        self._landmarker = mpVision.HandLandmarker.create_from_options(options)
        self._smoothedLm = None   # EMA-smoothed landmark cache

    # ── Core Detection ────────────────────────────────────────────────────────
    def detect(self, frame, timestampMs=None):
        """
        Run hand detection on a BGR `frame`.
        `timestampMs` must be a strictly-increasing int (milliseconds) when using
        VIDEO mode — pass `int(time.time() * 1000)` from the main loop.
        Returns (landmarks, handedness_label) for the first detected hand,
        or (None, None) when no hand is visible.
        `landmarks` is a list of 21 EMA-smoothed (x_px, y_px, z_norm) tuples.
        """
        if timestampMs is None:
            timestampMs = int(time.time() * 1000)

        rgbFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mpImage  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgbFrame)
        result   = self._landmarker.detect_for_video(mpImage, timestampMs)

        if not result.hand_landmarks:
            self._smoothedLm = None   # reset smoother when hand disappears
            return None, None

        h, w = frame.shape[:2]
        rawLm = result.hand_landmarks[0]
        rawLandmarks = [(int(lm.x * w), int(lm.y * h), lm.z) for lm in rawLm]
        landmarks = self._smoothLandmarks(rawLandmarks)

        handedness = "Unknown"
        if result.handedness:
            handedness = result.handedness[0][0].display_name

        return landmarks, handedness

    def _smoothLandmarks(self, landmarks):
        """Apply EMA smoothing to pixel positions to reduce jitter."""
        if self._smoothedLm is None:
            self._smoothedLm = landmarks[:]
            return landmarks
        a = config.EMA_ALPHA
        smoothed = [
            (int(a * rx + (1 - a) * sx),
             int(a * ry + (1 - a) * sy),
             rz)
            for (rx, ry, rz), (sx, sy, _) in zip(landmarks, self._smoothedLm)
        ]
        self._smoothedLm = smoothed
        return smoothed

    def drawLandmarks(self, frame, landmarks):
        """Draw hand skeleton overlay onto frame (in-place)."""
        if landmarks is None:
            return
        for c in HAND_CONNECTIONS:
            pt1 = landmarks[c[0]][:2]
            pt2 = landmarks[c[1]][:2]
            cv2.line(frame, pt1, pt2, (180, 180, 180), 1, cv2.LINE_AA)
        for lm in landmarks:
            cv2.circle(frame, lm[:2], 4, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, lm[:2], 4, (100, 100, 100),  1, cv2.LINE_AA)

    # ── Landmark Helpers ──────────────────────────────────────────────────────
    def getIndexTip(self, landmarks):
        """Return (x, y) pixel position of the index finger tip."""
        return landmarks[8][:2]

    def getThumbTip(self, landmarks):
        """Return (x, y) pixel position of the thumb tip."""
        return landmarks[4][:2]

    def _fingersUp(self, landmarks):
        """
        Return a list of booleans [thumb, index, middle, ring, pinky].
        Uses PIP joints (mid-finger bend) instead of MCP (knuckle) so that a
        partially curled finger is correctly classified as "down".
        """
        up = []

        # Thumb: horizontal check in mirrored frame — tip.x left of IP joint.x
        up.append(landmarks[TIP_IDS[0]][0] < landmarks[PIP_IDS[0]][0])

        # Fingers: tip.y strictly above PIP joint.y (smaller y = higher on screen)
        for i in range(1, 5):
            up.append(landmarks[TIP_IDS[i]][1] < landmarks[PIP_IDS[i]][1])

        return up

    # ── Gesture Classifiers ───────────────────────────────────────────────────
    def isThumbsUp(self, landmarks):
        """
        Thumbs-up: thumb tip clearly above its MCP joint (pointing upward)
        AND all four fingers are folded (tip below their PIP joints).
        """
        up = self._fingersUp(landmarks)
        # Thumb tip must be above thumb MCP (landmark 2) by a margin
        thumbPointingUp = landmarks[TIP_IDS[0]][1] < landmarks[BASE_IDS[0]][1] - 15
        return thumbPointingUp and not any(up[1:])

    def isDrawingMode(self, landmarks):
        """Index finger only is extended — draw mode."""
        up = self._fingersUp(landmarks)
        return up[1] and not up[2] and not up[3] and not up[4]

    def isEraserMode(self, landmarks):
        """Index + middle extended, others folded — erase mode."""
        up = self._fingersUp(landmarks)
        return up[1] and up[2] and not up[3] and not up[4]

    def isPalmOpen(self, landmarks):
        """All five fingers extended — clear canvas."""
        up = self._fingersUp(landmarks)
        return all(up[1:])   # ignore thumb for robustness

    def getPinchDistance(self, landmarks):
        """
        Normalised distance (0-1) between thumb tip and index tip.
        Used to control brush size dynamically.
        """
        tx, ty = self.getThumbTip(landmarks)
        ix, iy = self.getIndexTip(landmarks)
        # Normalise by approximate hand span (wrist to middle-finger MCP)
        wrist   = landmarks[0]
        midBase = landmarks[9]
        handSpan = math.hypot(midBase[0] - wrist[0], midBase[1] - wrist[1]) or 1
        dist = math.hypot(ix - tx, iy - ty)
        return min(dist / (handSpan * 2), 1.0)

    def isToolbarHover(self, landmarks):
        """Return True if the index tip is inside the toolbar zone."""
        _, y = self.getIndexTip(landmarks)
        return y < config.TOOLBAR_HEIGHT
