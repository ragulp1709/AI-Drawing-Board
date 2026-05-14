# backend/server.py — FastAPI web server for the AI Drawing Board

import sys
import os
import time
import threading
import cv2
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add backend/ to path so sibling modules (config, gesture_detector, etc.) are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from gesture_detector import GestureDetector
from drawing_board import DrawingBoard


# ── Shared State ──────────────────────────────────────────────────────────────

class SharedState:
    def __init__(self):
        self.appState         = config.STATE_IDLE
        self.brushSize        = config.DEFAULT_BRUSH_SIZE
        self.currentColorName = list(config.COLOR_PALETTE.keys())[0]
        self.isEraserActive   = False
        self.latestFrame      = None
        self.lock             = threading.Lock()

sharedState = SharedState()


# ── Background Processing Loop ────────────────────────────────────────────────

def processingLoop():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    ret, testFrame = cap.read()
    if not ret:
        print("[ERROR] Failed to read from webcam.")
        cap.release()
        return

    frameH, frameW = testFrame.shape[:2]
    detector = GestureDetector(maxHands=1, detectionConfidence=0.75, trackingConfidence=0.75)
    board    = DrawingBoard(frameW, frameH)

    appState      = config.STATE_IDLE
    debounceCount = 0
    pendingState  = None

    print("[INFO] Webcam processing loop started.")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        frame = cv2.flip(frame, 1)

        timestampMs      = int(time.time() * 1000)
        landmarks, _     = detector.detect(frame, timestampMs)
        indexTip          = None

        if landmarks:
            indexTip = detector.getIndexTip(landmarks)
            detector.drawLandmarks(frame, landmarks)

            if detector.isThumbsUp(landmarks):
                desiredState = config.STATE_DRAWING
            elif detector.isPalmOpen(landmarks):
                desiredState = "CLEAR"
            elif detector.isEraserMode(landmarks):
                desiredState = config.STATE_ERASING
            elif detector.isDrawingMode(landmarks):
                desiredState = config.STATE_DRAWING
            else:
                desiredState = appState

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

            onToolbar = detector.isToolbarHover(landmarks)
            if not onToolbar:
                board._hoverItemId = None
                board._hoverFrames = 0

            if onToolbar:
                board.resetStroke()
                board.checkToolbar(*indexTip)
            elif appState == config.STATE_DRAWING and not board.isEraserActive:
                board.draw(*indexTip)
            elif appState == config.STATE_DRAWING and board.isEraserActive:
                board.erase(*indexTip)
            elif appState == config.STATE_ERASING:
                board.erase(*indexTip)
            else:
                board.resetStroke()
        else:
            board.resetStroke()
            debounceCount = 0

        # ── Render pipeline ───────────────────────────────────────────────────
        board.renderCanvas(frame)
        hoverPos = indexTip if (landmarks and detector.isToolbarHover(landmarks)) else None
        board.renderToolbar(frame, hoverPos=hoverPos, appState=appState)
        board.renderCursor(frame, indexTip, appState)
        board.renderHUD(frame, appState, board.brushSize)

        if appState == config.STATE_IDLE:
            board.renderIdlePrompt(frame)

        # ── Encode and publish ────────────────────────────────────────────────
        _, jpegBuf   = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        jpegBytes    = jpegBuf.tobytes()

        colorName = list(config.COLOR_PALETTE.keys())[0]
        for name, bgr in config.COLOR_PALETTE.items():
            if list(bgr) == list(board.currentColor):
                colorName = name
                break

        with sharedState.lock:
            sharedState.latestFrame      = jpegBytes
            sharedState.appState         = appState
            sharedState.brushSize        = board.brushSize
            sharedState.currentColorName = colorName
            sharedState.isEraserActive   = board.isEraserActive

    cap.release()


# ── App Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=processingLoop, daemon=True)
    thread.start()
    yield


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(title="AI Drawing Board", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── MJPEG Video Stream ────────────────────────────────────────────────────────

def generateFrames():
    while True:
        with sharedState.lock:
            frame = sharedState.latestFrame

        if frame is None:
            time.sleep(0.03)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )
        time.sleep(0.033)   # ~30 fps cap


@app.get("/stream")
def videoStream():
    return StreamingResponse(
        generateFrames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ── REST API ──────────────────────────────────────────────────────────────────

@app.get("/api/state")
def getState():
    with sharedState.lock:
        appState         = sharedState.appState
        brushSize        = sharedState.brushSize
        colorName        = sharedState.currentColorName
        isEraserActive   = sharedState.isEraserActive

    colorBgr = config.COLOR_PALETTE.get(colorName, (0, 0, 255))
    colorHex = "#{:02x}{:02x}{:02x}".format(colorBgr[2], colorBgr[1], colorBgr[0])

    return {
        "state":          appState,
        "brushSize":      brushSize,
        "currentColor":   colorName,
        "colorHex":       "#555555" if isEraserActive else colorHex,
        "isEraserActive": isEraserActive,
    }


@app.get("/api/snapshot")
def getSnapshot():
    with sharedState.lock:
        frame = sharedState.latestFrame

    if frame is None:
        return Response(status_code=503, content="No frame available yet.")

    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Content-Disposition": "attachment; filename=drawing_snapshot.jpg"},
    )


# ── Frontend Static Files ─────────────────────────────────────────────────────

projectRoot  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontendDir  = os.path.join(projectRoot, "frontend")

app.mount("/static", StaticFiles(directory=frontendDir), name="static")


@app.get("/")
def index():
    htmlPath = os.path.join(frontendDir, "index.html")
    with open(htmlPath, "r") as f:
        return HTMLResponse(f.read())
