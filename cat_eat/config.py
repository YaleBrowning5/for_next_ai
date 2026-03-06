"""Static system-wide configuration for the cat feeding gate system."""

import os

# ---------------------------------------------------------------------------
# Camera settings
# ---------------------------------------------------------------------------
CAMERA_INDEX: int = int(os.environ.get("CAMERA_INDEX", "0"))
CAMERA_WIDTH: int = 640
CAMERA_HEIGHT: int = 480
CAMERA_FPS: int = 30

# ---------------------------------------------------------------------------
# Detection settings
# ---------------------------------------------------------------------------
DETECTION_CONFIDENCE: float = 0.5   # minimum MediaPipe detection confidence
DETECTION_QUEUE_SIZE: int = 4        # max frames waiting in the detection queue
IDENTIFICATION_QUEUE_SIZE: int = 4   # max detection results waiting for ID

# ---------------------------------------------------------------------------
# Embedding / identification settings
# ---------------------------------------------------------------------------
# Dimension of the flat image-patch embedding vector
EMBEDDING_DIM: int = 128
# Cosine-similarity threshold above which two embeddings are "same cat"
SIMILARITY_THRESHOLD: float = 0.80
# Minimum consecutive positive identifications before acting
MIN_ID_FRAMES: int = 3

# ---------------------------------------------------------------------------
# Door / FSM settings
# ---------------------------------------------------------------------------
# Seconds the door stays open after last positive ID before auto-closing
DOOR_OPEN_TIMEOUT: float = 8.0
# Seconds without detection before the system decides the cat has left
CAT_GONE_TIMEOUT: float = 2.0
# Simulated motor travel time (seconds) used by mock driver
DOOR_MOTOR_DURATION: float = 1.0

# ---------------------------------------------------------------------------
# Network / ESP32 settings (UDP mode)
# ---------------------------------------------------------------------------
ESP32_HOST: str = os.environ.get("ESP32_HOST", "192.168.31.88")
ESP32_PORT: int = int(os.environ.get("ESP32_PORT", "5005"))
UDP_TIMEOUT: float = 2.0

# ---------------------------------------------------------------------------
# SQLite config database
# ---------------------------------------------------------------------------
CONFIG_DB_PATH: str = os.environ.get("CONFIG_DB_PATH", "config.db")

# ---------------------------------------------------------------------------
# Web server settings
# ---------------------------------------------------------------------------
WEB_HOST: str = os.environ.get("WEB_HOST", "0.0.0.0")
WEB_PORT: int = int(os.environ.get("WEB_PORT", "8080"))
WEB_DEBUG: bool = False

# ---------------------------------------------------------------------------
# Target cat identifier stored in the config DB
# ---------------------------------------------------------------------------
TARGET_CAT_KEY: str = "target_cat"
