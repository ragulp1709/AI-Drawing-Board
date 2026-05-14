# main.py — Gesture Drawing Board entry point

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import cv2
import config
from gesture_detector import GestureDetector
from drawing_board    import DrawingBoard


def main():
    # ── Camera Setup ──────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam. Check that a camera is connected.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    # Read one frame to get the actual resolution (may differ from requested)
    ret, testFrame = cap.read()
    if not ret:
        print("[ERROR] Failed to read from webcam.")
        cap.release()
        sys.exit(1)

    frameH, frameW = testFrame.shape[:2]

    # ── Module Init ───────────────────────────────────────────────────────────
    detector = GestureDetector(maxHands=1, detectionConfidence=0.75, trackingConfidence=0.75)
    board    = DrawingBoard(frameW, frameH)

    # ── App State ─────────────────────────────────────────────────────────────
    appState      = config.STATE_IDLE
    debounceCount = 0          # frames the current gesture has been held
    pendingState  = None       # state we are counting toward

    print("[INFO] Gesture Drawing Board started.")
    print("       Show a thumbs-up to begin drawing.")
    print("       [ / ] keys  — decrease / increase brush size")
    print("       Press  q  to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Dropped frame.")
            continue

        # Mirror the frame so it behaves like a natural mirror
        frame = cv2.flip(frame, 1)

        # ── Hand Detection ────────────────────────────────────────────────────
        timestampMs      = int(time.time() * 1000)
        landmarks, _     = detector.detect(frame, timestampMs)
        indexTip          = None

        if landmarks:
            indexTip = detector.getIndexTip(landmarks)
            detector.drawLandmarks(frame, landmarks)

            # ── Gesture → Desired State ───────────────────────────────────────
            if detector.isThumbsUp(landmarks):
                desiredState = config.STATE_DRAWING
            elif detector.isPalmOpen(landmarks):
                desiredState = "CLEAR"
            elif detector.isEraserMode(landmarks):
                desiredState = config.STATE_ERASING
            elif detector.isDrawingMode(landmarks):
                desiredState = config.STATE_DRAWING
            else:
                desiredState = appState   # hold current state

            # ── Debounce ──────────────────────────────────────────────────────
            if desiredState != pendingState:
                pendingState  = desiredState
                debounceCount = 0
            else:
                debounceCount += 1

            if debounceCount >= config.GESTURE_DEBOUNCE_FRAMES:
                if pendingState == "CLEAR":
                    board.clear()
                    appState      = config.STATE_DRAWING
                    debounceCount = 0
                elif pendingState != appState:
                    appState      = pendingState
                    board.resetStroke()
                    debounceCount = 0

            # ── Toolbar Interaction ───────────────────────────────────────────
            onToolbar = detector.isToolbarHover(landmarks)
            if not onToolbar:
                board._hoverItemId = None
                board._hoverFrames = 0

            if onToolbar:
                board.resetStroke()
                board.checkToolbar(*indexTip)

            # ── Canvas Actions ────────────────────────────────────────────────
            elif appState == config.STATE_DRAWING and not board.isEraserActive:
                board.draw(*indexTip)

            elif appState == config.STATE_DRAWING and board.isEraserActive:
                board.erase(*indexTip)

            elif appState == config.STATE_ERASING:
                board.erase(*indexTip)

            else:
                # Not drawing or erasing — reset stroke so next draw starts fresh
                board.resetStroke()

        else:
            # No hand detected — keep canvas, reset stroke continuity
            board.resetStroke()
            debounceCount = 0

        # ── Rendering Pipeline ────────────────────────────────────────────────
        # 1. Composite drawing canvas onto webcam frame
        board.renderCanvas(frame)

        # 2. Toolbar (drawn on top of canvas composite)
        hoverPos = indexTip if (landmarks and detector.isToolbarHover(landmarks)) else None
        board.renderToolbar(frame, hoverPos=hoverPos, appState=appState)

        # 3. Cursor at index tip
        board.renderCursor(frame, indexTip, appState)

        # 4. HUD overlay
        board.renderHUD(frame, appState, board.brushSize)

        # 5. IDLE prompt
        if appState == config.STATE_IDLE:
            board.renderIdlePrompt(frame)

        # ── Display ───────────────────────────────────────────────────────────
        cv2.imshow(config.WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("[INFO] Quitting.")
            break
        elif key == ord("["):
            board.decreaseBrush()
        elif key == ord("]"):
            board.increaseBrush()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
