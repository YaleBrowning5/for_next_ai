"""UDP door driver for ESP32 over Wi-Fi.

Sends plain-text commands (``OPEN`` / ``CLOSE``) as UDP datagrams to the
ESP32 firmware running ``esp32/gate_udp.ino``.
"""

from __future__ import annotations

import logging
import socket

from .base import DoorCommand, DoorDriver

logger = logging.getLogger(__name__)


class UDPDriver(DoorDriver):
    """Send door commands to an ESP32 over UDP.

    Parameters
    ----------
    host:
        IP address of the ESP32.
    port:
        UDP port the ESP32 listens on (default 5005).
    timeout:
        Socket timeout in seconds.
    """

    def __init__(
        self,
        host: str = "192.168.31.88",
        port: int = 5005,
        timeout: float = 2.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command: DoorCommand) -> bool:
        payload = command.value.encode()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout)
                sock.sendto(payload, (self.host, self.port))
            logger.info("UDPDriver → %s:%d  %s", self.host, self.port, command.value)
            return True
        except OSError as exc:
            logger.error("UDPDriver send error: %s", exc)
            return False
