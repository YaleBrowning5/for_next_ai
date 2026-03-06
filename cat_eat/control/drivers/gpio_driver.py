"""GPIO door driver for Raspberry Pi.

Uses the ``RPi.GPIO`` library.  Automatically falls back to :class:`MockDriver`
on platforms where ``RPi.GPIO`` is not installed (e.g. Windows, CI servers).

Pin wiring
----------
- ``pin_open``  : HIGH → motor runs in "open" direction
- ``pin_close`` : HIGH → motor runs in "close" direction

Both pins LOW = motor stopped.
"""

from __future__ import annotations

import logging
import time

from .base import DoorCommand, DoorDriver

logger = logging.getLogger(__name__)


class GPIODriver(DoorDriver):
    """Control the door via Raspberry Pi GPIO pins.

    Parameters
    ----------
    pin_open:
        BCM pin number for the "open" relay.
    pin_close:
        BCM pin number for the "close" relay.
    motor_duration:
        Seconds to keep the motor relay active per command.
    """

    def __init__(
        self,
        pin_open: int = 17,
        pin_close: int = 27,
        motor_duration: float = 1.0,
    ) -> None:
        self.pin_open = pin_open
        self.pin_close = pin_close
        self.motor_duration = motor_duration
        self._gpio = None
        self._available = False
        self._setup()

    def _setup(self) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin_open, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.pin_close, GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO
            self._available = True
            logger.info(
                "GPIODriver ready (open_pin=%d, close_pin=%d).",
                self.pin_open,
                self.pin_close,
            )
        except Exception as exc:
            logger.warning(
                "RPi.GPIO not available (%s) — GPIO control disabled.", exc
            )

    def send(self, command: DoorCommand) -> bool:
        if not self._available or self._gpio is None:
            logger.warning("GPIODriver: hardware not available, command ignored: %s", command)
            return False

        GPIO = self._gpio
        try:
            if command == DoorCommand.OPEN:
                GPIO.output(self.pin_close, GPIO.LOW)
                GPIO.output(self.pin_open, GPIO.HIGH)
                time.sleep(self.motor_duration)
                GPIO.output(self.pin_open, GPIO.LOW)
            elif command == DoorCommand.CLOSE:
                GPIO.output(self.pin_open, GPIO.LOW)
                GPIO.output(self.pin_close, GPIO.HIGH)
                time.sleep(self.motor_duration)
                GPIO.output(self.pin_close, GPIO.LOW)
            logger.info("GPIODriver: %s executed.", command.value)
            return True
        except Exception as exc:
            logger.error("GPIODriver error: %s", exc)
            return False

    def cleanup(self) -> None:
        if self._gpio is not None:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
        logger.info("GPIODriver cleaned up.")
