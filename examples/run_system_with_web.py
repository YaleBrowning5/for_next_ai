#!/usr/bin/env python3
"""Main entry point: starts the full pipeline and the web server.

Usage
-----
::

    python examples/run_system_with_web.py

Environment variables
---------------------
CAMERA_INDEX  - camera device index (default 0)
ESP32_HOST    - ESP32 IP for UDP mode (default 192.168.31.88)
ESP32_PORT    - ESP32 UDP port (default 5005)
USE_GPIO      - set to "1" to use Raspberry Pi GPIO driver
USE_UDP       - set to "1" to use UDP (ESP32) driver
WEB_PORT      - web server port (default 8080)
CONFIG_DB_PATH- path to SQLite config database
"""

import logging
import os
import sys
import threading

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_driver():
    """Select the appropriate door driver based on environment variables."""
    use_gpio = os.environ.get("USE_GPIO", "0") == "1"
    use_udp = os.environ.get("USE_UDP", "0") == "1"

    if use_gpio:
        from cat_eat.control.drivers.gpio_driver import GPIODriver
        driver = GPIODriver()
        if driver._available:
            logger.info("Using GPIODriver.")
            return driver
        logger.warning("GPIODriver unavailable; falling back to MockDriver.")

    if use_udp:
        from cat_eat.config import ESP32_HOST, ESP32_PORT
        from cat_eat.control.drivers.udp_driver import UDPDriver
        logger.info("Using UDPDriver → %s:%d", ESP32_HOST, ESP32_PORT)
        return UDPDriver(host=ESP32_HOST, port=ESP32_PORT)

    logger.info("Using MockDriver (no hardware configured).")
    from cat_eat.control.drivers.mock_driver import MockDriver
    return MockDriver()


def main():
    from cat_eat.config import CONFIG_DB_PATH, WEB_HOST, WEB_PORT
    from cat_eat.control.config_manager import ConfigManager
    from cat_eat.pipeline import Pipeline
    from cat_eat.utils.state_cache import StateCache
    from web.server import create_app

    driver = build_driver()
    cache = StateCache()
    config = ConfigManager(CONFIG_DB_PATH)

    pipeline = Pipeline(driver=driver, state_cache=cache, config=config)

    # ------------------------------------------------------------------
    # Optional: load target cat from persistent config
    # ------------------------------------------------------------------
    target_cat = config.get("target_cat")
    if target_cat:
        logger.info("Target cat loaded from config: %s", target_cat)
    else:
        logger.info(
            "No target cat configured yet.  Use the API or register_cat() "
            "to enrol a cat before the door will open."
        )

    # ------------------------------------------------------------------
    # Start pipeline
    # ------------------------------------------------------------------
    pipeline.start()
    logger.info("Pipeline running.")

    # ------------------------------------------------------------------
    # Start web server (blocking)
    # ------------------------------------------------------------------
    app = create_app(
        state_cache=cache,
        fsm=pipeline.fsm,
        config_manager=config,
        identifier=pipeline.identifier,
    )

    logger.info("Web server starting at http://%s:%d", WEB_HOST, WEB_PORT)
    try:
        app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False)
    finally:
        pipeline.stop()
        config.close()
        logger.info("System shut down cleanly.")


if __name__ == "__main__":
    main()
