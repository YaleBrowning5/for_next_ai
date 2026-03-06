"""Unit tests for StateCache."""

import time
import threading
import unittest

from cat_eat.utils.state_cache import StateCache, get_default_cache


class TestStateCache(unittest.TestCase):

    def _make_cache(self):
        return StateCache()

    def test_initial_values(self):
        c = self._make_cache()
        self.assertEqual(c.get("door_state"), "IDLE")
        self.assertFalse(c.get("cat_detected"))

    def test_set_and_get(self):
        c = self._make_cache()
        c.set("door_state", "OPEN")
        self.assertEqual(c.get("door_state"), "OPEN")

    def test_update_multiple(self):
        c = self._make_cache()
        c.update({"cat_detected": True, "cat_id": "Nyan"})
        self.assertTrue(c.get("cat_detected"))
        self.assertEqual(c.get("cat_id"), "Nyan")

    def test_snapshot_is_copy(self):
        c = self._make_cache()
        snap = c.snapshot()
        snap["door_state"] = "MODIFIED"
        self.assertEqual(c.get("door_state"), "IDLE")

    def test_tick_frame_increments_count(self):
        c = self._make_cache()
        for _ in range(5):
            c.tick_frame()
        self.assertEqual(c.get("frame_count"), 5)

    def test_fps_computed_after_ticks(self):
        c = self._make_cache()
        for _ in range(10):
            c.tick_frame()
        # FPS may be very high in a tight loop; just check it's positive
        self.assertGreaterEqual(c.get("fps"), 0)

    def test_mark_detection_updates_state(self):
        c = self._make_cache()
        c.mark_detection("MiaoMiao", 0.92)
        self.assertTrue(c.get("cat_detected"))
        self.assertEqual(c.get("cat_id"), "MiaoMiao")
        self.assertAlmostEqual(c.get("similarity"), 0.92, places=2)
        self.assertIsNotNone(c.get("last_detection_ts"))

    def test_mark_detection_none_clears_cat(self):
        c = self._make_cache()
        c.mark_detection("MiaoMiao", 0.9)
        c.mark_detection(None, 0.0)
        self.assertFalse(c.get("cat_detected"))
        self.assertIsNone(c.get("cat_id"))

    def test_set_door_state(self):
        c = self._make_cache()
        c.set_door_state("OPEN")
        self.assertEqual(c.get("door_state"), "OPEN")
        self.assertIsNotNone(c.get("last_open_ts"))

    def test_set_error(self):
        c = self._make_cache()
        c.set_error("camera not found")
        self.assertEqual(c.get("error"), "camera not found")
        c.set_error(None)
        self.assertIsNone(c.get("error"))

    def test_thread_safety(self):
        c = self._make_cache()
        errors = []

        def writer():
            for i in range(100):
                try:
                    c.set("counter", i)
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(100):
                try:
                    _ = c.snapshot()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_default_cache_singleton(self):
        a = get_default_cache()
        b = get_default_cache()
        self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()
