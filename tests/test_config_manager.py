"""Unit tests for ConfigManager."""

import unittest

from cat_eat.control.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):

    def _make_cm(self) -> ConfigManager:
        return ConfigManager(":memory:")

    def test_set_and_get_string(self):
        cm = self._make_cm()
        cm.set("key1", "hello")
        self.assertEqual(cm.get("key1"), "hello")

    def test_set_and_get_int(self):
        cm = self._make_cm()
        cm.set("threshold", 42)
        self.assertEqual(cm.get("threshold"), 42)

    def test_set_and_get_float(self):
        cm = self._make_cm()
        cm.set("similarity", 0.85)
        self.assertAlmostEqual(cm.get("similarity"), 0.85, places=5)

    def test_set_and_get_dict(self):
        cm = self._make_cm()
        cm.set("profile", {"name": "Nyan", "count": 3})
        val = cm.get("profile")
        self.assertIsInstance(val, dict)
        self.assertEqual(val["name"], "Nyan")

    def test_default_returned_for_missing_key(self):
        cm = self._make_cm()
        self.assertIsNone(cm.get("nonexistent"))
        self.assertEqual(cm.get("nonexistent", "default_val"), "default_val")

    def test_update_existing_key(self):
        cm = self._make_cm()
        cm.set("x", 1)
        cm.set("x", 2)
        self.assertEqual(cm.get("x"), 2)

    def test_delete_key(self):
        cm = self._make_cm()
        cm.set("to_delete", "bye")
        cm.delete("to_delete")
        self.assertIsNone(cm.get("to_delete"))

    def test_all_returns_dict(self):
        cm = self._make_cm()
        cm.set("a", 1)
        cm.set("b", 2)
        result = cm.all()
        self.assertIn("a", result)
        self.assertIn("b", result)

    def test_close_does_not_raise(self):
        cm = self._make_cm()
        cm.set("k", "v")
        try:
            cm.close()
        except Exception as exc:
            self.fail(f"close() raised {exc}")


if __name__ == "__main__":
    unittest.main()
