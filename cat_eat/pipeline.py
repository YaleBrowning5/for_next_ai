"""Multi-threaded processing pipeline.

Thread layout
-------------
::

    CameraThread  →  detection_queue  →  DetectionThread
                                                │
                                         identification_queue
                                                │
                                         IdentificationThread  →  DoorFSM
                                                │
                                          StateCache  ←  WebServer reads

Each thread reads from its input queue and pushes results to the next.  Queues
are bounded so back-pressure propagates upstream and no queue grows unboundedly.

Graceful shutdown
-----------------
``Pipeline.stop()`` sets a stop event; each worker drains its queue and exits.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Optional

import numpy as np

from .config import (
    CAT_GONE_TIMEOUT,
    CAMERA_FPS,
    CAMERA_HEIGHT,
    CAMERA_INDEX,
    CAMERA_WIDTH,
    DETECTION_QUEUE_SIZE,
    DOOR_OPEN_TIMEOUT,
    IDENTIFICATION_QUEUE_SIZE,
    MIN_ID_FRAMES,
    SIMILARITY_THRESHOLD,
)
from .control.config_manager import ConfigManager
from .control.door_fsm import DoorFSM
from .control.drivers.base import DoorDriver
from .control.drivers.mock_driver import MockDriver
from .utils.state_cache import StateCache, get_default_cache
from .vision.cat_identifier import CatIdentifier
from .vision.mediapipe_detector import MediaPipeDetector

logger = logging.getLogger(__name__)

# Sentinel value pushed to queues to signal shutdown
_STOP_SENTINEL = object()


class Pipeline:
    """Orchestrates the detection → identification → FSM data flow.

    Parameters
    ----------
    driver:
        Door hardware driver.  Defaults to :class:`MockDriver`.
    state_cache:
        Shared state cache.  Defaults to the module-level singleton.
    config:
        Persistent config manager.  Defaults to an in-memory store.
    """

    def __init__(
        self,
        driver: Optional[DoorDriver] = None,
        state_cache: Optional[StateCache] = None,
        config: Optional[ConfigManager] = None,
    ) -> None:
        self._driver = driver or MockDriver()
        self._cache = state_cache or get_default_cache()
        self._config = config or ConfigManager(":memory:")

        self._detector = MediaPipeDetector(min_confidence=0.5)
        self._identifier = CatIdentifier(
            similarity_threshold=SIMILARITY_THRESHOLD,
            embedding_dim=128,
        )
        self._fsm = DoorFSM(
            driver=self._driver,
            open_timeout=DOOR_OPEN_TIMEOUT,
            cat_gone_timeout=CAT_GONE_TIMEOUT,
            min_id_frames=MIN_ID_FRAMES,
            on_state_change=self._on_door_state_change,
        )

        self._detection_q: queue.Queue = queue.Queue(maxsize=DETECTION_QUEUE_SIZE)
        self._identification_q: queue.Queue = queue.Queue(maxsize=IDENTIFICATION_QUEUE_SIZE)

        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

        self._cap = None  # OpenCV VideoCapture, created in start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def fsm(self) -> DoorFSM:
        return self._fsm

    @property
    def identifier(self) -> CatIdentifier:
        return self._identifier

    @property
    def state_cache(self) -> StateCache:
        return self._cache

    def start(self) -> None:
        """Start all pipeline threads."""
        logger.info("Pipeline starting…")
        self._stop_event.clear()

        self._threads = [
            threading.Thread(target=self._camera_loop, name="CameraThread", daemon=True),
            threading.Thread(target=self._detection_loop, name="DetectionThread", daemon=True),
            threading.Thread(target=self._identification_loop, name="IDThread", daemon=True),
            threading.Thread(target=self._fsm_tick_loop, name="FSMTickThread", daemon=True),
        ]
        for t in self._threads:
            t.start()
        logger.info("Pipeline started with %d threads.", len(self._threads))

    def stop(self) -> None:
        """Signal all threads to stop and wait for them to exit."""
        logger.info("Pipeline stopping…")
        self._stop_event.set()
        # Unblock queues
        try:
            self._detection_q.put_nowait(_STOP_SENTINEL)
        except queue.Full:
            pass
        try:
            self._identification_q.put_nowait(_STOP_SENTINEL)
        except queue.Full:
            pass
        for t in self._threads:
            t.join(timeout=5.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._driver.cleanup()
        logger.info("Pipeline stopped.")

    def register_cat(self, cat_id: str, roi: np.ndarray) -> bool:
        """Add a reference image for *cat_id*."""
        return self._identifier.register_from_roi(cat_id, roi)

    # ------------------------------------------------------------------
    # Thread workers
    # ------------------------------------------------------------------

    def _camera_loop(self) -> None:
        try:
            import cv2  # type: ignore

            self._cap = cv2.VideoCapture(CAMERA_INDEX)
            if not self._cap.isOpened():
                logger.error("Cannot open camera %d.", CAMERA_INDEX)
                self._cache.set_error(f"Cannot open camera {CAMERA_INDEX}")
                return
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self._cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        except ImportError:
            logger.error("OpenCV not available; camera thread exiting.")
            return

        logger.info("CameraThread started.")
        while not self._stop_event.is_set():
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Camera read failed.")
                time.sleep(0.05)
                continue
            self._cache.tick_frame()
            # Non-blocking put; drop frame if detection queue is full
            try:
                self._detection_q.put_nowait(frame)
            except queue.Full:
                pass
        logger.info("CameraThread exiting.")

    def _detection_loop(self) -> None:
        logger.info("DetectionThread started.")
        while not self._stop_event.is_set():
            try:
                item = self._detection_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is _STOP_SENTINEL:
                break
            frame: np.ndarray = item
            detections = self._detector.detect(frame)
            # Forward best detection (highest confidence) to ID queue
            if detections:
                best = max(detections, key=lambda d: d.confidence)
                payload = (best, frame)
            else:
                payload = (None, frame)
            try:
                self._identification_q.put_nowait(payload)
            except queue.Full:
                pass
        logger.info("DetectionThread exiting.")

    def _identification_loop(self) -> None:
        logger.info("IDThread started.")
        while not self._stop_event.is_set():
            try:
                item = self._identification_q.get(timeout=0.5)
            except queue.Empty:
                # Queue stall — do NOT feed None to the FSM; the FSM's own
                # timer thread (on_tick) handles timeout-driven transitions.
                continue
            if item is _STOP_SENTINEL:
                break
            detection, _frame = item
            if detection is None:
                id_result_cat = None
                similarity = 0.0
            else:
                id_result = self._identifier.identify(detection)
                id_result_cat = id_result.cat_id
                similarity = id_result.similarity

            self._cache.mark_detection(id_result_cat, similarity)
            self._fsm.on_detection(id_result_cat, similarity)
        logger.info("IDThread exiting.")

    def _fsm_tick_loop(self) -> None:
        """Advance timer-driven FSM transitions periodically."""
        logger.info("FSMTickThread started.")
        while not self._stop_event.is_set():
            self._fsm.on_tick()
            self._cache.set_door_state(self._fsm.state.value)
            time.sleep(0.5)
        logger.info("FSMTickThread exiting.")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_door_state_change(self, new_state) -> None:
        self._cache.set_door_state(new_state.value)
        logger.info("Door state changed to: %s", new_state.value)
