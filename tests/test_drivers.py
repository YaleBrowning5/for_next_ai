"""Unit tests for door hardware drivers."""

import unittest

from cat_eat.control.drivers.base import DoorCommand, DoorDriver
from cat_eat.control.drivers.mock_driver import MockDriver
from cat_eat.control.drivers.udp_driver import UDPDriver


class TestMockDriver(unittest.TestCase):

    def test_send_open_returns_true(self):
        d = MockDriver()
        self.assertTrue(d.send(DoorCommand.OPEN))

    def test_send_close_returns_true(self):
        d = MockDriver()
        self.assertTrue(d.send(DoorCommand.CLOSE))

    def test_history_recorded(self):
        d = MockDriver()
        d.open()
        d.close()
        self.assertEqual(d.commands_sent(), [DoorCommand.OPEN, DoorCommand.CLOSE])

    def test_last_command(self):
        d = MockDriver()
        d.open()
        self.assertEqual(d.last_command, DoorCommand.OPEN)
        d.close()
        self.assertEqual(d.last_command, DoorCommand.CLOSE)

    def test_reset_clears_history(self):
        d = MockDriver()
        d.open()
        d.reset()
        self.assertEqual(d.history, [])
        self.assertIsNone(d.last_command)

    def test_open_close_convenience_methods(self):
        d = MockDriver()
        d.open()
        d.close()
        cmds = d.commands_sent()
        self.assertIn(DoorCommand.OPEN, cmds)
        self.assertIn(DoorCommand.CLOSE, cmds)


class TestDriverAbstractBase(unittest.TestCase):

    def test_cannot_instantiate_abstract_driver(self):
        with self.assertRaises(TypeError):
            DoorDriver()  # abstract class

    def test_mock_is_subclass(self):
        self.assertTrue(issubclass(MockDriver, DoorDriver))


class TestUDPDriver(unittest.TestCase):
    """Tests for UDPDriver — we only test that it constructs and fails
    gracefully when the target host is unreachable."""

    def test_construction(self):
        d = UDPDriver(host="127.0.0.1", port=59999, timeout=0.1)
        self.assertEqual(d.host, "127.0.0.1")
        self.assertEqual(d.port, 59999)

    def test_send_to_unreachable_host_returns_false(self):
        # UDP sendto itself doesn't fail (no connection), so this should succeed
        # unless there is a network error; either way, no exception should propagate.
        d = UDPDriver(host="192.0.2.1", port=59999, timeout=0.1)
        result = d.send(DoorCommand.OPEN)
        # Result may be True (sent) or False (OS error), but no exception
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
