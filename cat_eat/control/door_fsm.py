"""Door finite-state machine (FSM).

States
------
::

    IDLE
     │  cat detected (not yet confirmed)
     ▼
    DETECTING
     │  >= MIN_ID_FRAMES consecutive positive IDs
     ▼
    VERIFYING ──► IDLE  (failed to verify in time)
     │  verified
     ▼
    OPENING
     │  driver.open() completed
     ▼
    OPEN ──► WAITING (timer starts)
     │        │  DOOR_OPEN_TIMEOUT expires or cat gone
     ▼        ▼
    CLOSING
     │  driver.close() completed
     ▼
    IDLE

Transitions that can happen from any state
- ``reset()`` → IDLE (e.g. emergency stop)
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Callable, Optional

from .drivers.base import DoorCommand, DoorDriver

logger = logging.getLogger(__name__)


class DoorState(str, enum.Enum):
    IDLE = "IDLE"
    DETECTING = "DETECTING"
    VERIFYING = "VERIFYING"
    OPENING = "OPENING"
    OPEN = "OPEN"
    WAITING = "WAITING"
    CLOSING = "CLOSING"


class DoorFSM:
    """Thread-safe door controller FSM.

    Parameters
    ----------
    driver:
        Hardware driver that executes ``OPEN`` / ``CLOSE`` commands.
    open_timeout:
        Seconds the door remains in OPEN/WAITING before auto-closing.
    cat_gone_timeout:
        Seconds without a positive detection before declaring the cat gone.
    min_id_frames:
        Number of consecutive positive identifications before opening.
    on_state_change:
        Optional callback called with the new :class:`DoorState` whenever
        the FSM transitions.
    """

    def __init__(
        self,
        driver: DoorDriver,
        open_timeout: float = 8.0,
        cat_gone_timeout: float = 2.0,
        min_id_frames: int = 3,
        on_state_change: Optional[Callable[[DoorState], None]] = None,
    ) -> None:
        self._driver = driver
        self.open_timeout = open_timeout
        self.cat_gone_timeout = cat_gone_timeout
        self.min_id_frames = min_id_frames
        self._on_state_change = on_state_change

        self._lock = threading.RLock()
        self._state = DoorState.IDLE
        self._confirmed_cat_id: Optional[str] = None
        self._consecutive_hits: int = 0
        self._last_hit_ts: float = 0.0
        self._open_ts: float = 0.0

        # Background timer thread for auto-close
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_timer = threading.Event()

    # ------------------------------------------------------------------
    # Public read-only properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> DoorState:
        with self._lock:
            return self._state

    @property
    def confirmed_cat_id(self) -> Optional[str]:
        with self._lock:
            return self._confirmed_cat_id

    # ------------------------------------------------------------------
    # Event inputs (called by the pipeline)
    # ------------------------------------------------------------------

    def on_detection(self, cat_id: Optional[str], similarity: float) -> None:
        """Feed a detection event into the FSM.

        Parameters
        ----------
        cat_id:
            Identified cat ID (``None`` if no cat or unknown cat).
        similarity:
            Cosine similarity score for the best match.
        """
        with self._lock:
            now = time.monotonic()
            if cat_id is not None:
                self._last_hit_ts = now
                if self._state == DoorState.IDLE:
                    self._confirmed_cat_id = cat_id
                    self._consecutive_hits = 1
                    self._transition(DoorState.DETECTING)
                    if self._consecutive_hits >= self.min_id_frames:
                        self._transition(DoorState.VERIFYING)
                elif self._state == DoorState.DETECTING:
                    if cat_id == self._confirmed_cat_id or self._confirmed_cat_id is None:
                        self._confirmed_cat_id = cat_id
                        self._consecutive_hits += 1
                        if self._consecutive_hits >= self.min_id_frames:
                            self._transition(DoorState.VERIFYING)
                    else:
                        # Different cat detected – restart
                        self._consecutive_hits = 1
                        self._confirmed_cat_id = cat_id
                elif self._state in (DoorState.OPEN, DoorState.WAITING):
                    # Cat still present → keep door open, reset timer
                    self._open_ts = now
                    if self._state == DoorState.WAITING:
                        self._transition(DoorState.OPEN)
            else:
                # No detection
                if self._state == DoorState.DETECTING:
                    elapsed = now - self._last_hit_ts
                    if elapsed > self.cat_gone_timeout:
                        self._consecutive_hits = 0
                        self._confirmed_cat_id = None
                        self._transition(DoorState.IDLE)
                elif self._state in (DoorState.OPEN, DoorState.WAITING):
                    elapsed = now - self._last_hit_ts
                    if elapsed > self.cat_gone_timeout:
                        self._transition(DoorState.WAITING)

            # Drive the VERIFYING → OPENING transition immediately
            if self._state == DoorState.VERIFYING:
                self._execute_open()

    def on_tick(self) -> None:
        """Call periodically (e.g. every 500 ms) to advance timer-driven transitions."""
        with self._lock:
            now = time.monotonic()
            if self._state in (DoorState.OPEN, DoorState.WAITING):
                if now - self._open_ts > self.open_timeout:
                    self._execute_close()

    def manual_open(self) -> bool:
        """Manually open the door, bypassing normal detection flow.

        Forces the FSM to IDLE first, then sends the open command directly and
        transitions to OPEN so the state stays consistent.
        """
        with self._lock:
            logger.info("DoorFSM: manual open requested.")
            self._consecutive_hits = 0
            self._confirmed_cat_id = None
            self._stop_timer.set()
            success = self._driver.open()
            if success:
                self._open_ts = time.monotonic()
                self._transition(DoorState.OPEN)
            else:
                self._transition(DoorState.IDLE)
            return success

    def manual_close(self) -> bool:
        """Manually close the door and return to IDLE."""
        with self._lock:
            logger.info("DoorFSM: manual close requested.")
            self._stop_timer.set()
            success = self._driver.close()
            self._consecutive_hits = 0
            self._confirmed_cat_id = None
            self._transition(DoorState.IDLE)
            return success

    def reset(self) -> None:
        """Force the FSM back to IDLE (emergency stop)."""
        with self._lock:
            logger.warning("DoorFSM.reset() called – forcing IDLE.")
            self._stop_timer.set()
            if self._state in (DoorState.OPEN, DoorState.WAITING, DoorState.OPENING):
                self._driver.close()
            self._consecutive_hits = 0
            self._confirmed_cat_id = None
            self._transition(DoorState.IDLE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(self, new_state: DoorState) -> None:
        """Transition to *new_state* and invoke the callback."""
        old_state = self._state
        self._state = new_state
        logger.info("DoorFSM: %s → %s", old_state.value, new_state.value)
        if self._on_state_change is not None:
            try:
                self._on_state_change(new_state)
            except Exception as exc:
                logger.error("on_state_change callback error: %s", exc)

    def _execute_open(self) -> None:
        """Initiate the OPENING sequence."""
        self._transition(DoorState.OPENING)
        cat_id = self._confirmed_cat_id
        # Run the motor command in a separate thread so the FSM lock is not
        # held while a potentially blocking driver call executes.
        t = threading.Thread(target=self._open_then_transition, args=(cat_id,), daemon=True)
        t.start()

    def _open_then_transition(self, cat_id: Optional[str]) -> None:
        success = self._driver.open()
        with self._lock:
            if success:
                self._open_ts = time.monotonic()
                self._transition(DoorState.OPEN)
            else:
                logger.error("Door open command failed.")
                self._transition(DoorState.IDLE)

    def _execute_close(self) -> None:
        """Initiate the CLOSING sequence."""
        self._transition(DoorState.CLOSING)
        t = threading.Thread(target=self._close_then_transition, daemon=True)
        t.start()

    def _close_then_transition(self) -> None:
        success = self._driver.close()
        with self._lock:
            self._consecutive_hits = 0
            self._confirmed_cat_id = None
            if success:
                self._transition(DoorState.IDLE)
            else:
                logger.error("Door close command failed.")
                self._transition(DoorState.IDLE)
