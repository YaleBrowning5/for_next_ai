"""Unit tests for DoorFSM.

Tests use MockDriver to avoid touching any real hardware.
"""

import time
import threading
import unittest

from cat_eat.control.door_fsm import DoorFSM, DoorState
from cat_eat.control.drivers.mock_driver import MockDriver
from cat_eat.control.drivers.base import DoorCommand


class TestDoorFSMBasic(unittest.TestCase):

    def _make_fsm(self, min_id_frames=3, open_timeout=5.0, cat_gone_timeout=1.0):
        driver = MockDriver()
        fsm = DoorFSM(
            driver=driver,
            open_timeout=open_timeout,
            cat_gone_timeout=cat_gone_timeout,
            min_id_frames=min_id_frames,
        )
        return fsm, driver

    # ------------------------------------------------------------------
    # Initial state
    # ------------------------------------------------------------------

    def test_initial_state_is_idle(self):
        fsm, _ = self._make_fsm()
        self.assertEqual(fsm.state, DoorState.IDLE)

    # ------------------------------------------------------------------
    # IDLE → DETECTING
    # ------------------------------------------------------------------

    def test_first_detection_moves_to_detecting(self):
        fsm, _ = self._make_fsm(min_id_frames=3)
        fsm.on_detection("cat_a", 0.9)
        self.assertEqual(fsm.state, DoorState.DETECTING)

    def test_no_detection_stays_idle(self):
        fsm, _ = self._make_fsm()
        fsm.on_detection(None, 0.0)
        self.assertEqual(fsm.state, DoorState.IDLE)

    # ------------------------------------------------------------------
    # DETECTING → VERIFYING / OPENING → OPEN
    # ------------------------------------------------------------------

    def test_consecutive_detections_open_door(self):
        fsm, driver = self._make_fsm(min_id_frames=2)
        fsm.on_detection("cat_a", 0.95)  # hit 1 → DETECTING
        fsm.on_detection("cat_a", 0.95)  # hit 2 → VERIFYING → OPENING → OPEN

        # Give the background thread time to complete
        deadline = time.monotonic() + 2.0
        while fsm.state != DoorState.OPEN and time.monotonic() < deadline:
            time.sleep(0.05)

        self.assertEqual(fsm.state, DoorState.OPEN)
        self.assertIn(DoorCommand.OPEN, driver.commands_sent())

    # ------------------------------------------------------------------
    # Auto-close on timeout
    # ------------------------------------------------------------------

    def test_auto_close_after_timeout(self):
        fsm, driver = self._make_fsm(min_id_frames=1, open_timeout=0.2)
        fsm.on_detection("cat_a", 0.95)  # → VERIFYING → OPENING → OPEN

        deadline = time.monotonic() + 2.0
        while fsm.state != DoorState.OPEN and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(fsm.state, DoorState.OPEN)

        # Wait for timeout then tick
        time.sleep(0.4)
        fsm.on_tick()

        deadline = time.monotonic() + 2.0
        while fsm.state not in (DoorState.IDLE, DoorState.CLOSING) and time.monotonic() < deadline:
            time.sleep(0.05)

        self.assertIn(DoorCommand.CLOSE, driver.commands_sent())

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def test_reset_forces_idle(self):
        fsm, driver = self._make_fsm(min_id_frames=1)
        fsm.on_detection("cat_a", 0.9)
        # Wait to reach OPEN
        deadline = time.monotonic() + 2.0
        while fsm.state != DoorState.OPEN and time.monotonic() < deadline:
            time.sleep(0.05)
        fsm.reset()
        self.assertEqual(fsm.state, DoorState.IDLE)

    # ------------------------------------------------------------------
    # State change callback
    # ------------------------------------------------------------------

    def test_state_change_callback_fires(self):
        states = []
        driver = MockDriver()
        fsm = DoorFSM(
            driver=driver,
            min_id_frames=1,
            on_state_change=lambda s: states.append(s),
        )
        fsm.on_detection("cat_a", 0.9)
        deadline = time.monotonic() + 2.0
        while DoorState.OPEN not in states and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertIn(DoorState.OPEN, states)

    # ------------------------------------------------------------------
    # Different cat resets detection count
    # ------------------------------------------------------------------

    def test_different_cat_resets_counter(self):
        fsm, _ = self._make_fsm(min_id_frames=3)
        fsm.on_detection("cat_a", 0.9)
        fsm.on_detection("cat_b", 0.9)  # different → resets counter
        self.assertEqual(fsm._consecutive_hits, 1)
        self.assertEqual(fsm._confirmed_cat_id, "cat_b")


class TestDoorFSMCatGone(unittest.TestCase):

    def test_cat_gone_resets_detecting(self):
        driver = MockDriver()
        fsm = DoorFSM(driver=driver, min_id_frames=5, cat_gone_timeout=0.1)
        fsm.on_detection("cat_a", 0.9)
        self.assertEqual(fsm.state, DoorState.DETECTING)
        time.sleep(0.3)
        fsm.on_detection(None, 0.0)
        self.assertEqual(fsm.state, DoorState.IDLE)


if __name__ == "__main__":
    unittest.main()
