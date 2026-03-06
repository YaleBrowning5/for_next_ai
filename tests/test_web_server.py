"""Unit tests for the Flask web server.

Uses Flask's test client — no network required.
"""

import json
import unittest

from cat_eat.control.config_manager import ConfigManager
from cat_eat.control.door_fsm import DoorFSM
from cat_eat.control.drivers.mock_driver import MockDriver
from cat_eat.utils.state_cache import StateCache
from cat_eat.vision.cat_identifier import CatIdentifier
from web.server import create_app


def _make_app():
    cache = StateCache()
    driver = MockDriver()
    fsm = DoorFSM(driver=driver, min_id_frames=1)
    config = ConfigManager(":memory:")
    identifier = CatIdentifier(embedding_dim=64)
    app = create_app(
        state_cache=cache,
        fsm=fsm,
        config_manager=config,
        identifier=identifier,
    )
    app.config["TESTING"] = True
    return app, cache, fsm, config, identifier


class TestWebServerRoutes(unittest.TestCase):

    def setUp(self):
        self.app, self.cache, self.fsm, self.config, self.identifier = _make_app()
        self.client = self.app.test_client()

    def test_index_returns_200(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"<html", r.data.lower())

    def test_api_status_returns_json(self):
        r = self.client.get("/api/status")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn("door_state", data)
        self.assertIn("cat_detected", data)
        self.assertIn("fps", data)

    def test_api_status_reflects_cache(self):
        self.cache.set_door_state("OPEN")
        r = self.client.get("/api/status")
        data = json.loads(r.data)
        self.assertEqual(data["door_state"], "OPEN")

    def test_api_status_includes_registered_cats(self):
        import numpy as np
        roi = np.zeros((32, 32, 3), dtype=np.uint8)
        self.identifier.register_from_roi("Nyan", roi)
        r = self.client.get("/api/status")
        data = json.loads(r.data)
        self.assertIn("Nyan", data["registered_cats"])

    def test_api_door_close_returns_ok(self):
        r = self.client.post("/api/door/close")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertTrue(data["ok"])

    def test_api_door_open_returns_ok(self):
        r = self.client.post("/api/door/open")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertTrue(data["ok"])

    def test_api_config_get_empty(self):
        r = self.client.get("/api/config")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIsInstance(data, dict)

    def test_api_config_post_and_get(self):
        payload = json.dumps({"target_cat": "MiaoMiao", "threshold": 0.85})
        self.client.post(
            "/api/config",
            data=payload,
            content_type="application/json",
        )
        r = self.client.get("/api/config")
        data = json.loads(r.data)
        self.assertEqual(data.get("target_cat"), "MiaoMiao")
        self.assertAlmostEqual(data.get("threshold"), 0.85, places=5)

    def test_api_cats_empty(self):
        r = self.client.get("/api/cats")
        data = json.loads(r.data)
        self.assertIn("cats", data)
        self.assertIsInstance(data["cats"], list)

    def test_api_door_no_fsm_returns_503(self):
        app_no_fsm, _, _, config, identifier = _make_app()
        # Re-create app without FSM
        cache = StateCache()
        app_no_fsm = create_app(
            state_cache=cache,
            fsm=None,
            config_manager=config,
            identifier=identifier,
        )
        app_no_fsm.config["TESTING"] = True
        c = app_no_fsm.test_client()
        r = c.post("/api/door/open")
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
