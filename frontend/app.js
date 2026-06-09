// app.js — Frontend logic for the AI Drawing Board

// ── Constants ──────────────────────────────────────────────────────────────

const STATE_IDLE    = "IDLE";
const STATE_DRAWING = "DRAWING";
const STATE_ERASING = "ERASING";

const DEFAULT_API_BASE_URL = "https://ai-drawing-board-1.onrender.com";
const API_BASE_URL =
  window.AI_DRAWING_BOARD_API_URL ||
  document.body.dataset.apiBaseUrl ||
  DEFAULT_API_BASE_URL;

const POLL_INTERVAL_MS = 500;
const MIN_BRUSH_SIZE   = 3;
const MAX_BRUSH_SIZE   = 40;

// Tailwind class sets for each app state
const stateTheme = {
  [STATE_IDLE]:    { dot: "bg-gray-500",  label: "text-gray-400",  bar: "bg-gray-500"  },
  [STATE_DRAWING]: { dot: "bg-green-400", label: "text-green-400", bar: "bg-green-400" },
  [STATE_ERASING]: { dot: "bg-blue-400",  label: "text-blue-400",  bar: "bg-blue-400"  },
};

// ── Element References ─────────────────────────────────────────────────────

const videoStreamEl    = document.getElementById("videoStream");
const loadingOverlayEl = document.getElementById("loadingOverlay");
const connDotEl        = document.getElementById("connDot");
const connLabelEl      = document.getElementById("connLabel");
const stateDotEl       = document.getElementById("stateDot");
const stateLabelEl     = document.getElementById("stateLabel");
const colorSwatchEl    = document.getElementById("colorSwatch");
const colorLabelEl     = document.getElementById("colorLabel");
const brushSizeLabelEl = document.getElementById("brushSizeLabel");
const brushBarEl       = document.getElementById("brushBar");
const saveBtnEl        = document.getElementById("saveBtn");

videoStreamEl.src = `${API_BASE_URL}/stream`;
saveBtnEl.href = `${API_BASE_URL}/api/snapshot`;

// ── Stream Load Detection ──────────────────────────────────────────────────

videoStreamEl.addEventListener("load", () => {
  loadingOverlayEl.classList.add("hidden");
  setConnected(true);
});

videoStreamEl.addEventListener("error", () => {
  loadingOverlayEl.classList.remove("hidden");
  setConnected(false);
});

// ── Connection Badge ───────────────────────────────────────────────────────

function setConnected(isConnected) {
  const dotClasses   = isConnected ? "bg-green-400" : "bg-red-500";
  const labelText    = isConnected ? "Connected"    : "Disconnected";
  const labelClasses = isConnected ? "text-gray-400" : "text-red-400";

  connDotEl.className  = `w-2 h-2 rounded-full ${dotClasses}`;
  connLabelEl.className = `text-xs ${labelClasses}`;
  connLabelEl.textContent = labelText;
}

// ── State Panel Update ─────────────────────────────────────────────────────

function applyThemeClasses(el, oldClasses, newClasses) {
  oldClasses.split(" ").forEach((cls) => el.classList.remove(cls));
  newClasses.split(" ").forEach((cls) => el.classList.add(cls));
}

function updatePanel(data) {
  const { state, brushSize, currentColor, colorHex, isEraserActive } = data;

  // State badge
  const theme = stateTheme[state] || stateTheme[STATE_IDLE];

  applyThemeClasses(
    stateDotEl,
    "bg-gray-500 bg-green-400 bg-blue-400",
    theme.dot
  );
  applyThemeClasses(
    stateLabelEl,
    "text-gray-400 text-green-400 text-blue-400",
    theme.label
  );
  stateLabelEl.textContent = state;

  // Color swatch
  colorSwatchEl.style.backgroundColor = colorHex;
  colorLabelEl.textContent = isEraserActive ? "Eraser" : currentColor;

  // Brush bar
  brushSizeLabelEl.textContent = `${brushSize} px`;
  const pct = ((brushSize - MIN_BRUSH_SIZE) / (MAX_BRUSH_SIZE - MIN_BRUSH_SIZE)) * 100;
  brushBarEl.style.width = `${Math.max(4, pct)}%`;

  applyThemeClasses(
    brushBarEl,
    "bg-gray-500 bg-green-400 bg-blue-400 bg-blue-500",
    theme.bar
  );
}

// ── State Polling ──────────────────────────────────────────────────────────

async function pollState() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/state`);
    if (res.ok) {
      const data = await res.json();
      updatePanel(data);
      setConnected(true);
    } else {
      setConnected(false);
    }
  } catch (_) {
    setConnected(false);
  }
}

// Kick off immediately, then repeat
pollState();
setInterval(pollState, POLL_INTERVAL_MS);
