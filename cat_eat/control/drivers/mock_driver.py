"""Mock door driver — records commands without touching real hardware.

Used in unit tests and on platforms where GPIO/UDP are unavailable.
"""

from __future__ import annotations

import logging
import time
from typing import List, Tuple

from .base import DoorCommand, DoorDriver

logger = logging.getLogger(__name__)


class MockDriver(DoorDriver):
    """In-memory door driver that records every command sent.

    Attributes
    ----------
    history : list of (timestamp, DoorCommand)
        Ordered log of all commands received since creation (or last reset).
    last_command : DoorCommand | None
        The most recently received command.
    """

    def __init__(self, motor_duration: float = 0.0) -> None:
        self.motor_duration = motor_duration
        self.history: List[Tuple[float, DoorCommand]] = []
        self.last_command: DoorCommand | None = None

    def send(self, command: DoorCommand) -> bool:
        logger.debug("MockDriver received: %s", command.value)
        self.history.append((time.monotonic(), command))
        self.last_command = command
        if self.motor_duration > 0:
            time.sleep(self.motor_duration)
        return True

    def reset(self) -> None:
        self.history.clear()
        self.last_command = None

    def commands_sent(self) -> List[DoorCommand]:
        return [cmd for _, cmd in self.history]
