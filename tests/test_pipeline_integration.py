"""Integration test: Pipeline with mock detector and mock driver.

Replaces the camera thread with a synthetic frame generator so no real
camera or MediaPipe model is required.
"""

import queue
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from cat_eat.control.door_fsm import DoorFSM, DoorState
from cat_eat.control.drivers.mock_driver import MockDriver
from cat_eat.control.drivers.base import DoorCommand
from cat_eat.control.config_manager import ConfigManager
from cat_eat.utils.state_cache import StateCache
from cat_eat.vision.cat_identifier import CatIdentifier
from cat_eat.vision.embedding import compute_embedding
from cat_eat.vision.mediapipe_detector import DetectionResult


class TestPipelineIntegration(unittest.TestCase):
    """Tests the full identification → FSM flow without a real camera."""

    def _setup(self):
        self.driver = MockDriver()
        self.cache = StateCache()
        self.config = ConfigManager(":memory:")
        self.identifier = CatIdentifier(similarity_threshold=0.99, embedding_dim=128)

        self.fsm = DoorFSM(
            driver=self.driver,
            open_timeout=5.0,
            cat_gone_timeout=1.0,
            min_id_frames=2,
            on_state_change=lambda s: self.cache.set_door_state(s.value),
        )
        return self

    def test_full_id_flow_opens_door(self):
        """Simulate 3 consecutive detections of the registered cat."""
        self._setup()
        roi = np.random.default_rng(42).integers(0, 255, (32, 32, 3), dtype=np.uint8)
        emb = compute_embedding(roi, dim=128)
        self.identifier.register("MiaoMiao", [emb])

        det = DetectionResult(bbox=(0, 0, 32, 32), confidence=0.9, label="cat", roi=roi)

        for _ in range(3):
            result = self.identifier.identify(det)
            self.fsm.on_detection(result.cat_id, result.similarity)

        # Wait for background thread to open door
        deadline = time.monotonic() + 3.0
        while self.fsm.state != DoorState.OPEN and time.monotonic() < deadline:
            time.sleep(0.05)

        self.assertEqual(self.fsm.state, DoorState.OPEN)
        self.assertIn(DoorCommand.OPEN, self.driver.commands_sent())
        self.assertEqual(self.cache.get("door_state"), "OPEN")

    def test_unknown_cat_does_not_open_door(self):
        """An unregistered cat should not trigger the door."""
        self._setup()
        # Register a known cat
        known_roi = np.random.default_rng(1).integers(0, 255, (32, 32, 3), dtype=np.uint8)
        emb = compute_embedding(known_roi, dim=128)
        self.identifier.register("Known", [emb])

        # Feed a completely different ROI (unknown cat)
        unknown_roi = np.random.default_rng(99).integers(0, 255, (32, 32, 3), dtype=np.uint8)
        unknown_det = DetectionResult(
            bbox=(0, 0, 32, 32), confidence=0.9, label="cat", roi=unknown_roi
        )
        for _ in range(5):
            result = self.identifier.identify(unknown_det)
            self.fsm.on_detection(result.cat_id, result.similarity)

        time.sleep(0.1)
        self.assertNotIn(DoorCommand.OPEN, self.driver.commands_sent())

    def test_door_closes_after_timeout(self):
        """After opening, the door should close automatically after timeout."""
        self._setup()
        self.fsm.open_timeout = 0.3
        roi = np.random.default_rng(7).integers(0, 255, (32, 32, 3), dtype=np.uint8)
        emb = compute_embedding(roi, dim=128)
        self.identifier.register("Nyan", [emb])

        det = DetectionResult(bbox=(0, 0, 32, 32), confidence=0.95, label="cat", roi=roi)
        for _ in range(3):
            result = self.identifier.identify(det)
            self.fsm.on_detection(result.cat_id, result.similarity)

        # Wait for OPEN
        deadline = time.monotonic() + 3.0
        while self.fsm.state != DoorState.OPEN and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(self.fsm.state, DoorState.OPEN)

        # Wait for timeout
        time.sleep(0.5)
        self.fsm.on_tick()

        deadline = time.monotonic() + 3.0
        while self.fsm.state == DoorState.OPEN and time.monotonic() < deadline:
            time.sleep(0.05)

        self.assertIn(DoorCommand.CLOSE, self.driver.commands_sent())


class TestStateCacheIntegration(unittest.TestCase):

    def test_state_cache_thread_safe_writes(self):
        cache = StateCache()
        errors = []

        def worker(cat_id):
            for _ in range(50):
                try:
                    cache.mark_detection(cat_id, 0.9)
                    cache.set_door_state("OPEN")
                    _ = cache.snapshot()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"cat_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
