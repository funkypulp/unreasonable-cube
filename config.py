# config.py — CubeBot with_hardware settings

import os

# ── Hardware ──────────────────────────────────────────────────────
# Single ESP32-S3 for now (one screen + one encoder test)
# Find your port: ls /dev/cu.usb* in terminal
SERIAL_PORTS = [
    "/dev/cu.usbserial-0001",    # ← update this to your actual port
]
BAUD_RATE = 115200

# ── Voice ─────────────────────────────────────────────────────────
WAKE_PHRASE    = "hey cube"
WHISPER_MODEL  = "tiny.en"
SILENCE_SEC    = 1.0
MAX_RECORD_SEC = 8
SAMPLE_RATE    = 16000

# ── Wake mode ─────────────────────────────────────────────────────
# "enter" → press Enter to start  (easiest for testing)
# "voice" → say "hey cube"
WAKE_MODE = "enter"

# ── AI ────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-5"
MAX_FOLLOWUPS     = 4

# ── Cube faces ────────────────────────────────────────────────────
COLORS     = ["red", "orange", "yellow", "green", "blue", "white"]
FACE_COUNT = 6

# ── Encoder weights ───────────────────────────────────────────────
WEIGHT_STEP = 0.10
WEIGHT_MIN  = 0.05
WEIGHT_MAX  = 1.0

# ── Hardware mode ─────────────────────────────────────────────────
USE_MOCK_HARDWARE = False   # always False in this folder
