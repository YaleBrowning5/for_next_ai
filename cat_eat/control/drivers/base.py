"""Abstract door hardware driver.

All concrete drivers (GPIO, UDP, Mock) inherit from :class:`DoorDriver` and
implement :meth:`send`.  This keeps the :class:`~cat_eat.control.door_fsm.DoorFSM`
completely independent of the physical control channel.
"""

from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DoorCommand(str, enum.Enum):
    """Commands that can be sent to the door hardware."""
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    STATUS = "STATUS"


class DoorDriver(ABC):
    """Abstract base class for door actuator drivers."""

    @abstractmethod
    def send(self, command: DoorCommand) -> bool:
        """Send *command* to the door hardware.

        Returns
        -------
        bool
            *True* on success, *False* on failure.
        """

    def open(self) -> bool:
        """Convenience wrapper for ``send(OPEN)``."""
        return self.send(DoorCommand.OPEN)

    def close(self) -> bool:
        """Convenience wrapper for ``send(CLOSE)``."""
        return self.send(DoorCommand.CLOSE)

    def cleanup(self) -> None:
        """Release any hardware resources.  Override as needed."""
