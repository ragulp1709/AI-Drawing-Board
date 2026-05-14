# config.py — all constants for the Gesture Drawing Board

# ── Window ────────────────────────────────────────────────────────────────────
WINDOW_NAME = "Gesture Drawing Board"
FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720

# ── Toolbar ───────────────────────────────────────────────────────────────────
TOOLBAR_HEIGHT   = 80       # pixels from top of frame
SWATCH_PADDING   = 10       # gap between swatches
SWATCH_SIZE      = 60       # width and height of each color tile

# ── Colors (BGR) ──────────────────────────────────────────────────────────────
# Palette used for drawing; order determines left-to-right toolbar position
COLOR_PALETTE = {
    "Red":    (0,   0,   255),
    "Orange": (0,   128, 255),
    "Yellow": (0,   255, 255),
    "Green":  (0,   200, 0  ),
    "Blue":   (255, 100, 0  ),
    "Purple": (200, 0,   200),
    "White":  (255, 255, 255),
}

ERASER_COLOR  = (0, 0, 0)           # black — treated as "erase"
TOOLBAR_BG    = (30, 30, 30)        # dark toolbar background
HIGHLIGHT_COLOR = (255, 255, 255)   # swatch border when selected / hovered

# ── Brush ─────────────────────────────────────────────────────────────────────
DEFAULT_BRUSH_SIZE = 8
MIN_BRUSH_SIZE     = 3
MAX_BRUSH_SIZE     = 40
ERASER_SIZE        = 30
BRUSH_STEP         = 3     # increment for +/- buttons and [ ] keys

# Hold-to-repeat for toolbar +/- buttons
HOLD_DELAY_FRAMES  = 15   # frames before repeat starts (~0.5 s)
HOLD_REPEAT_FRAMES = 8    # fire every N frames during hold (~3-4 x/sec)

# Pinch distance thresholds (normalised, 0-1 scale)
PINCH_MIN_DIST = 0.04   # fully pinched → min brush
PINCH_MAX_DIST = 0.25   # fully open → max brush

# ── Gesture thresholds ────────────────────────────────────────────────────────
# Minimum fraction of hand height that a finger must extend above its base
# to be considered "up".
FINGER_UP_THRESHOLD    = 0.1
# Minimum frames a gesture must persist before the state changes (debounce)
GESTURE_DEBOUNCE_FRAMES = 4

# Exponential moving average alpha for landmark smoothing (0=frozen, 1=raw)
EMA_ALPHA = 0.5

# ── HUD ───────────────────────────────────────────────────────────────────────
HUD_FONT       = 1          # cv2.FONT_HERSHEY_SIMPLEX equivalent integer
HUD_FONT_SCALE = 0.7
HUD_THICKNESS  = 2
HUD_COLOR      = (220, 220, 220)
HUD_BG_COLOR   = (30, 30, 30)

# ── App States ────────────────────────────────────────────────────────────────
STATE_IDLE    = "IDLE"
STATE_DRAWING = "DRAWING"
STATE_ERASING = "ERASING"
