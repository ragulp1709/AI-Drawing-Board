# drawing_board.py — Canvas management, toolbar rendering, and frame compositing

import cv2
import numpy as np
import config


# ── UI Helpers ────────────────────────────────────────────────────────────────
def _rr(frame, x1, y1, x2, y2, radius, color, thickness=-1):
    """Draw a filled or outlined rounded rectangle."""
    r = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    if thickness == -1:
        cv2.rectangle(frame, (x1 + r, y1), (x2 - r, y2), color, -1)
        cv2.rectangle(frame, (x1, y1 + r), (x2, y2 - r), color, -1)
        cv2.ellipse(frame, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, -1)
        cv2.ellipse(frame, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, -1)
        cv2.ellipse(frame, (x1 + r, y2 - r), (r, r), 90,  0, 90, color, -1)
        cv2.ellipse(frame, (x2 - r, y2 - r), (r, r), 0,   0, 90, color, -1)
    else:
        cv2.line(frame, (x1 + r, y1), (x2 - r, y1), color, thickness)
        cv2.line(frame, (x1 + r, y2), (x2 - r, y2), color, thickness)
        cv2.line(frame, (x1, y1 + r), (x1, y2 - r), color, thickness)
        cv2.line(frame, (x2, y1 + r), (x2, y2 - r), color, thickness)
        cv2.ellipse(frame, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
        cv2.ellipse(frame, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
        cv2.ellipse(frame, (x1 + r, y2 - r), (r, r), 90,  0, 90, color, thickness)
        cv2.ellipse(frame, (x2 - r, y2 - r), (r, r), 0,   0, 90, color, thickness)


class DrawingBoard:
    def __init__(self, width, height):
        self.width  = width
        self.height = height

        # BGRA canvas — alpha channel lets us composite onto webcam cleanly
        self.canvas = np.zeros((height, width, 4), dtype=np.uint8)

        # Drawing state
        self.currentColor     = list(config.COLOR_PALETTE.values())[0]
        self.brushSize        = config.DEFAULT_BRUSH_SIZE
        self.eraserSize       = config.ERASER_SIZE
        self.prevPoint        = None   # for smooth line interpolation
        self.isEraserActive   = False

        # Toolbar hover / hold-to-repeat state
        self._hoverItemId  = None
        self._hoverFrames  = 0

        # Build toolbar layout once
        self._buildToolbar()

    # ── Toolbar Setup ─────────────────────────────────────────────────────────
    def _buildToolbar(self):
        """Pre-compute bounding boxes for every toolbar tile."""
        self.toolbarItems = []   # list of dicts: {label, color, rect}
        x = config.SWATCH_PADDING

        for name, bgr in config.COLOR_PALETTE.items():
            rect = (x, config.SWATCH_PADDING,
                    x + config.SWATCH_SIZE,
                    config.SWATCH_PADDING + config.SWATCH_SIZE)
            self.toolbarItems.append({"label": name, "color": bgr, "rect": rect, "isEraser": False, "isClear": False})
            x += config.SWATCH_SIZE + config.SWATCH_PADDING

        # Eraser tile
        rect = (x, config.SWATCH_PADDING,
                x + config.SWATCH_SIZE,
                config.SWATCH_PADDING + config.SWATCH_SIZE)
        self.toolbarItems.append({"label": "Eraser", "color": (60, 60, 60), "rect": rect, "isEraser": True, "isClear": False})
        x += config.SWATCH_SIZE + config.SWATCH_PADDING

        # Decrease brush tile
        rect = (x, config.SWATCH_PADDING,
                x + config.SWATCH_SIZE,
                config.SWATCH_PADDING + config.SWATCH_SIZE)
        self.toolbarItems.append({"label": "-", "color": (80, 40, 100), "rect": rect, "isEraser": False, "isClear": False, "isDecrease": True})
        x += config.SWATCH_SIZE + config.SWATCH_PADDING

        # Increase brush tile
        rect = (x, config.SWATCH_PADDING,
                x + config.SWATCH_SIZE,
                config.SWATCH_PADDING + config.SWATCH_SIZE)
        self.toolbarItems.append({"label": "+", "color": (40, 100, 60), "rect": rect, "isEraser": False, "isClear": False, "isIncrease": True})
        x += config.SWATCH_SIZE + config.SWATCH_PADDING

        # Clear tile
        rect = (x, config.SWATCH_PADDING,
                x + config.SWATCH_SIZE,
                config.SWATCH_PADDING + config.SWATCH_SIZE)
        self.toolbarItems.append({"label": "Clear", "color": (0, 80, 180), "rect": rect, "isEraser": False, "isClear": True})

    # ── Canvas Operations ─────────────────────────────────────────────────────
    def draw(self, x, y):
        """Draw a smooth stroke from the previous point to (x, y)."""
        color_bgra = (*self.currentColor, 255)
        if self.prevPoint is not None:
            cv2.line(self.canvas, self.prevPoint, (x, y),
                     color_bgra, self.brushSize, cv2.LINE_AA)
        else:
            cv2.circle(self.canvas, (x, y), self.brushSize // 2,
                       color_bgra, -1, cv2.LINE_AA)
        self.prevPoint = (x, y)

    def erase(self, x, y):
        """Erase an area around (x, y) by zeroing the alpha channel."""
        if self.prevPoint is not None:
            cv2.line(self.canvas, self.prevPoint, (x, y),
                     (0, 0, 0, 0), self.eraserSize * 2, cv2.LINE_AA)
        else:
            cv2.circle(self.canvas, (x, y), self.eraserSize,
                       (0, 0, 0, 0), -1, cv2.LINE_AA)
        self.prevPoint = (x, y)

    def clear(self):
        """Wipe the entire canvas."""
        self.canvas[:] = 0
        self.prevPoint = None

    def resetStroke(self):
        """Call when the drawing finger lifts to start a new stroke."""
        self.prevPoint = None

    def setBrushSize(self, normalizedDist):
        """Map a normalised pinch distance (0-1) to brush size."""
        t = (normalizedDist - config.PINCH_MIN_DIST) / (
            config.PINCH_MAX_DIST - config.PINCH_MIN_DIST)
        t = max(0.0, min(1.0, t))
        self.brushSize = int(
            config.MIN_BRUSH_SIZE + t * (config.MAX_BRUSH_SIZE - config.MIN_BRUSH_SIZE)
        )

    def increaseBrush(self):
        """Step brush size up by BRUSH_STEP."""
        self.brushSize = min(self.brushSize + config.BRUSH_STEP, config.MAX_BRUSH_SIZE)

    def decreaseBrush(self):
        """Step brush size down by BRUSH_STEP."""
        self.brushSize = max(self.brushSize - config.BRUSH_STEP, config.MIN_BRUSH_SIZE)

    # ── Toolbar Interaction ───────────────────────────────────────────────────
    def checkToolbar(self, x, y):
        """
        If (x, y) is over a toolbar tile, activate it.
        +/- use hold-to-repeat; color/eraser/clear are single-shot on first touch.
        Returns True if any tile is hit.
        """
        for item in self.toolbarItems:
            x1, y1, x2, y2 = item["rect"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                itemId = id(item)
                if itemId != self._hoverItemId:
                    # Finger just entered this tile
                    self._hoverItemId = itemId
                    self._hoverFrames = 0
                else:
                    self._hoverFrames += 1

                if item.get("isDecrease") or item.get("isIncrease"):
                    # Hold-to-repeat: fire on frame 0, then every HOLD_REPEAT_FRAMES
                    # after an initial HOLD_DELAY_FRAMES pause
                    framesAfterDelay = self._hoverFrames - config.HOLD_DELAY_FRAMES
                    shouldFire = (
                        self._hoverFrames == 0 or
                        (framesAfterDelay >= 0 and
                         framesAfterDelay % config.HOLD_REPEAT_FRAMES == 0)
                    )
                    if shouldFire:
                        if item.get("isDecrease"):
                            self.decreaseBrush()
                        else:
                            self.increaseBrush()

                elif self._hoverFrames == 0:   # single-shot for other tiles
                    if item["isClear"]:
                        self.clear()
                    elif item["isEraser"]:
                        self.isEraserActive = True
                    else:
                        self.currentColor   = item["color"]
                        self.isEraserActive = False
                return True

        # Finger left the toolbar area — reset hold state
        self._hoverItemId = None
        self._hoverFrames = 0
        return False

    # ── Rendering ─────────────────────────────────────────────────────────────
    def renderToolbar(self, frame, hoverPos=None, appState=None):
        """Draw the modern toolbar strip onto `frame` (in-place, BGR)."""
        tbH = config.TOOLBAR_HEIGHT
        w   = self.width

        # Frosted dark background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, tbH), (12, 14, 22), -1)
        cv2.addWeighted(overlay, 0.90, frame, 0.10, 0, frame)

        # Bottom separator glow
        cv2.line(frame, (0, tbH - 1), (w, tbH - 1), (50, 55, 80), 1)
        cv2.line(frame, (0, tbH),     (w, tbH),     (22, 24, 36), 1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cy   = tbH // 2   # vertical center of toolbar

        for item in self.toolbarItems:
            x1, y1, x2, y2 = item["rect"]
            cx = (x1 + x2) // 2

            isHovered = (
                hoverPos is not None and
                x1 <= hoverPos[0] <= x2 and
                y1 <= hoverPos[1] <= y2
            )
            isActive = (
                not item["isClear"] and
                not item["isEraser"] and
                not item.get("isDecrease") and
                not item.get("isIncrease") and
                item["color"] == self.currentColor and
                not self.isEraserActive
            ) or (item["isEraser"] and self.isEraserActive)

            isDecrease = item.get("isDecrease", False)
            isIncrease = item.get("isIncrease", False)
            isClear    = item["isClear"]
            isEraser   = item["isEraser"]
            isColor    = not isClear and not isEraser and not isDecrease and not isIncrease

            if isColor:
                r = 24
                color = item["color"]
                # Drop shadow
                cv2.circle(frame, (cx + 2, cy + 2), r, (0, 0, 0), -1)
                # Outer glow ring when active
                if isActive:
                    cv2.circle(frame, (cx, cy), r + 6, (255, 255, 255), 2)
                elif isHovered:
                    cv2.circle(frame, (cx, cy), r + 5, (160, 160, 180), 1)
                # Fill
                cv2.circle(frame, (cx, cy), r, color, -1)
                # Subtle dark edge
                cv2.circle(frame, (cx, cy), r, (0, 0, 0), 1)
                # Active checkmark dot
                if isActive:
                    cv2.circle(frame, (cx, cy), 6, (255, 255, 255), -1)
                    cv2.circle(frame, (cx, cy), 6, color, 2)

            elif isEraser:
                r = 24
                bg = (75, 75, 90) if isHovered else (55, 55, 70)
                cv2.circle(frame, (cx + 2, cy + 2), r, (0, 0, 0), -1)
                cv2.circle(frame, (cx, cy), r, bg, -1)
                ringColor = (240, 240, 240) if isActive else ((170, 170, 190) if isHovered else (90, 90, 110))
                cv2.circle(frame, (cx, cy), r, ringColor, 2 if isActive else 1)
                if isActive:
                    cv2.circle(frame, (cx, cy), r + 5, (255, 255, 255), 1)
                # × symbol
                cv2.line(frame, (cx - 9, cy - 9), (cx + 9, cy + 9), (210, 210, 220), 2, cv2.LINE_AA)
                cv2.line(frame, (cx + 9, cy - 9), (cx - 9, cy + 9), (210, 210, 220), 2, cv2.LINE_AA)

            elif isDecrease or isIncrease:
                bw, bh = 46, 30
                bx1, by1 = cx - bw // 2, cy - bh // 2
                bx2, by2 = cx + bw // 2, cy + bh // 2
                if isDecrease:
                    bgBase, bgHov = (75, 45, 110), (100, 65, 145)
                    border        = (170, 120, 230)
                else:
                    bgBase, bgHov = (35, 100, 60), (50, 135, 80)
                    border        = (100, 230, 140)
                bg = bgHov if isHovered else bgBase
                _rr(frame, bx1, by1, bx2, by2, 10, bg, -1)
                _rr(frame, bx1, by1, bx2, by2, 10, border, 1)
                sym = item["label"]
                (tw, th), _ = cv2.getTextSize(sym, font, 0.9, 2)
                cv2.putText(frame, sym, (cx - tw // 2, cy + th // 2 - 1),
                            font, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

            elif isClear:
                bw, bh = 46, 30
                bx1, by1 = cx - bw // 2, cy - bh // 2
                bx2, by2 = cx + bw // 2, cy + bh // 2
                bg = (55, 55, 215) if isHovered else (38, 38, 170)
                _rr(frame, bx1, by1, bx2, by2, 10, bg, -1)
                _rr(frame, bx1, by1, bx2, by2, 10, (110, 110, 255), 1)
                (tw, th), _ = cv2.getTextSize("CLR", font, 0.38, 1)
                cv2.putText(frame, "CLR", (cx - tw // 2, cy + th // 2 - 1),
                            font, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

    def renderCanvas(self, frame):
        """Alpha-composite the drawing canvas onto the webcam frame."""
        alpha = self.canvas[:, :, 3:4].astype(np.float32) / 255.0
        for c in range(3):
            frame[:, :, c] = (
                self.canvas[:, :, c] * alpha[:, :, 0] +
                frame[:, :, c] * (1.0 - alpha[:, :, 0])
            ).astype(np.uint8)

    def renderHUD(self, frame, appState, brushSize):
        """Draw a frosted-glass status card in the bottom-left corner."""
        px, py = 14, self.height - 98
        pw, ph = 220, 84

        stateColors = {
            config.STATE_IDLE:    (150, 150, 160),
            config.STATE_DRAWING: (70,  215,  70),
            config.STATE_ERASING: (70,  170, 255),
        }
        stateColor = stateColors.get(appState, (255, 255, 255))
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Frosted background card
        overlay = frame.copy()
        _rr(overlay, px, py, px + pw, py + ph, 12, (14, 16, 26), -1)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
        _rr(frame, px, py, px + pw, py + ph, 12, (45, 50, 75), 1)

        # Mode row: colored dot + label
        dotX, dotY = px + 18, py + 24
        cv2.circle(frame, (dotX, dotY), 5, stateColor, -1)
        cv2.putText(frame, appState, (dotX + 12, dotY + 5),
                    font, 0.55, stateColor, 1, cv2.LINE_AA)

        # Color preview circle (top-right of card)
        swatchColor = (55, 55, 72) if self.isEraserActive else self.currentColor
        cv2.circle(frame, (px + pw - 22, py + 24), 13, swatchColor, -1)
        cv2.circle(frame, (px + pw - 22, py + 24), 13, (70, 75, 100), 1)
        if self.isEraserActive:
            cv2.line(frame, (px + pw - 29, py + 17), (px + pw - 15, py + 31), (180, 180, 190), 1, cv2.LINE_AA)
            cv2.line(frame, (px + pw - 15, py + 17), (px + pw - 29, py + 31), (180, 180, 190), 1, cv2.LINE_AA)

        # Brush label
        cv2.putText(frame, f"Brush  {brushSize}px", (px + 18, py + 52),
                    font, 0.46, (140, 145, 165), 1, cv2.LINE_AA)

        # Brush progress bar
        barX1, barY1 = px + 18,      py + 60
        barX2, barY2 = px + pw - 18, py + 70
        barW = barX2 - barX1
        fillW = max(0, int(barW * (brushSize - config.MIN_BRUSH_SIZE) /
                           max(config.MAX_BRUSH_SIZE - config.MIN_BRUSH_SIZE, 1)))
        _rr(frame, barX1, barY1, barX2, barY2, 4, (35, 38, 55), -1)
        if fillW > 6:
            _rr(frame, barX1, barY1, barX1 + fillW, barY2, 4, stateColor, -1)

    def renderIdlePrompt(self, frame):
        """Overlay a modern centered card prompting the user to begin."""
        font  = cv2.FONT_HERSHEY_SIMPLEX
        line1, line2 = "Raise your hand", "Thumbs-up to start drawing"
        s1, s2       = 0.9, 0.62
        (w1, h1), _  = cv2.getTextSize(line1, font, s1, 2)
        (w2, h2), _  = cv2.getTextSize(line2, font, s2, 1)
        cardW = max(w1, w2) + 48
        cardH = h1 + h2 + 44
        cx = (self.width  - cardW) // 2
        cy = self.height // 2 - cardH // 2

        # Frosted card background
        overlay = frame.copy()
        _rr(overlay, cx, cy, cx + cardW, cy + cardH, 16, (14, 16, 26), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        _rr(frame, cx, cy, cx + cardW, cy + cardH, 16, (55, 90, 160), 2)

        # Accent top bar
        _rr(frame, cx, cy, cx + cardW, cy + 4, 2, (55, 140, 255), -1)

        # Line 1 — big label
        tx1 = cx + (cardW - w1) // 2
        ty1 = cy + h1 + 14
        cv2.putText(frame, line1, (tx1 + 1, ty1 + 1), font, s1, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, line1, (tx1, ty1), font, s1, (255, 255, 255), 2, cv2.LINE_AA)

        # Line 2 — sub-label
        tx2 = cx + (cardW - w2) // 2
        ty2 = ty1 + h2 + 16
        cv2.putText(frame, line2, (tx2, ty2), font, s2, (0, 210, 255), 1, cv2.LINE_AA)

    def renderCursor(self, frame, pos, appState):
        """Draw a modern cursor at the index-finger tip position."""
        if pos is None:
            return
        cx, cy = pos

        if appState == config.STATE_ERASING:
            # Eraser: blue ring + center dot
            cv2.circle(frame, (cx, cy), self.eraserSize,     (30, 30, 30),    3, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), self.eraserSize,     (80, 180, 255),  2, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 3,                   (80, 180, 255), -1, cv2.LINE_AA)

        elif appState == config.STATE_DRAWING:
            r     = max(self.brushSize // 2, 5)
            color = (55, 55, 72) if self.isEraserActive else self.currentColor
            # Dark shadow ring
            cv2.circle(frame, (cx + 1, cy + 1), r + 3, (0, 0, 0),   2, cv2.LINE_AA)
            # Color ring
            cv2.circle(frame, (cx, cy),          r + 3, color,       2, cv2.LINE_AA)
            # White center dot with dark outline
            cv2.circle(frame, (cx, cy),          4,     (0, 0, 0),  -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy),          3,     (255, 255, 255), -1, cv2.LINE_AA)

        else:
            # Idle: animated-ish concentric rings
            cv2.circle(frame, (cx, cy), 14, (0, 0, 0),       2, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 13, (0, 210, 255),   1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy),  5, (0, 210, 255),  -1, cv2.LINE_AA)
