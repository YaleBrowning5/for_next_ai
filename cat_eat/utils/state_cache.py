"""Thread-safe in-memory state cache shared across the pipeline and web layer.

Intentional design:
- Real-time pipeline state is kept **only in memory** (no DB writes on every
  frame).  SQLite is used exclusively for persistent *settings*.
- The web server reads a shallow copy of this cache; it never writes to it
  directly and never blocks the detection pipeline.
"""

import threading
import time
from typing import Any, Dict, Optional


class StateCache:
    """Thread-safe key-value store for live system state."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {
            "door_state": "IDLE",
            "cat_detected": False,
            "cat_id": None,
            "similarity": 0.0,
            "frame_count": 0,
            "last_detection_ts": None,
            "last_open_ts": None,
            "fps": 0.0,
            "error": None,
        }
        self._frame_times: list = []

    # ------------------------------------------------------------------
    # Core get / set / update
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def update(self, mapping: Dict[str, Any]) -> None:
        with self._lock:
            self._data.update(mapping)

    def snapshot(self) -> Dict[str, Any]:
        """Return a shallow copy safe to hand to external consumers."""
        with self._lock:
            return dict(self._data)

    # ------------------------------------------------------------------
    # Helpers used by the camera thread for FPS tracking
    # ------------------------------------------------------------------

    def tick_frame(self) -> None:
        """Call once per captured frame to update FPS and frame count."""
        now = time.monotonic()
        with self._lock:
            self._data["frame_count"] += 1
            self._frame_times.append(now)
            # keep only last 30 timestamps
            if len(self._frame_times) > 30:
                self._frame_times = self._frame_times[-30:]
            if len(self._frame_times) >= 2:
                elapsed = self._frame_times[-1] - self._frame_times[0]
                if elapsed > 0:
                    self._data["fps"] = round(
                        (len(self._frame_times) - 1) / elapsed, 1
                    )

    def mark_detection(self, cat_id: Optional[str], similarity: float) -> None:
        with self._lock:
            self._data["cat_detected"] = cat_id is not None
            self._data["cat_id"] = cat_id
            self._data["similarity"] = round(similarity, 3)
            if cat_id is not None:
                self._data["last_detection_ts"] = time.time()

    def set_door_state(self, state: str) -> None:
        with self._lock:
            self._data["door_state"] = state
            if state == "OPEN":
                self._data["last_open_ts"] = time.time()

    def set_error(self, msg: Optional[str]) -> None:
        with self._lock:
            self._data["error"] = msg


# Module-level singleton used by default
_default_cache: Optional[StateCache] = None
_cache_lock = threading.Lock()


def get_default_cache() -> StateCache:
    global _default_cache
    with _cache_lock:
        if _default_cache is None:
            _default_cache = StateCache()
        return _default_cache
