"""Flask web server providing real-time status and manual control.

Design rules:
- Reads **only** from the :class:`~cat_eat.utils.state_cache.StateCache`.
- Never touches the pipeline threads directly.
- Manual open/close commands go through the door FSM, not the driver.
"""

from __future__ import annotations

import logging
from typing import Optional

from flask import Flask, jsonify, render_template, request

logger = logging.getLogger(__name__)


def create_app(
    state_cache=None,
    fsm=None,
    config_manager=None,
    identifier=None,
) -> Flask:
    """Application factory.

    Parameters
    ----------
    state_cache:
        :class:`~cat_eat.utils.state_cache.StateCache` instance.
    fsm:
        :class:`~cat_eat.control.door_fsm.DoorFSM` instance.
    config_manager:
        :class:`~cat_eat.control.config_manager.ConfigManager` instance.
    identifier:
        :class:`~cat_eat.vision.cat_identifier.CatIdentifier` instance.
    """
    from cat_eat.control.config_manager import ConfigManager
    from cat_eat.control.door_fsm import DoorFSM
    from cat_eat.utils.state_cache import get_default_cache

    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Resolve defaults
    _cache = state_cache or get_default_cache()
    _fsm: Optional[DoorFSM] = fsm
    _config: Optional[ConfigManager] = config_manager
    _identifier = identifier

    # -----------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/status")
    def api_status():
        """Return a JSON snapshot of the current system state."""
        snap = _cache.snapshot()
        snap["registered_cats"] = _identifier.list_cats() if _identifier else []
        return jsonify(snap)

    @app.route("/api/door/open", methods=["POST"])
    def api_door_open():
        if _fsm is None:
            return jsonify({"ok": False, "error": "FSM not available"}), 503
        success = _fsm.manual_open()
        _cache.set_door_state(_fsm.state.value)
        return jsonify({"ok": success, "state": _fsm.state.value})

    @app.route("/api/door/close", methods=["POST"])
    def api_door_close():
        if _fsm is None:
            return jsonify({"ok": False, "error": "FSM not available"}), 503
        success = _fsm.manual_close()
        _cache.set_door_state(_fsm.state.value)
        return jsonify({"ok": success, "state": _fsm.state.value})

    @app.route("/api/config", methods=["GET"])
    def api_config_get():
        if _config is None:
            return jsonify({}), 503
        return jsonify(_config.all())

    @app.route("/api/config", methods=["POST"])
    def api_config_set():
        if _config is None:
            return jsonify({"ok": False, "error": "Config not available"}), 503
        data = request.get_json(force=True, silent=True) or {}
        for k, v in data.items():
            _config.set(k, v)
        return jsonify({"ok": True})

    @app.route("/api/cats", methods=["GET"])
    def api_cats():
        cats = _identifier.list_cats() if _identifier else []
        return jsonify({"cats": cats})

    return app
