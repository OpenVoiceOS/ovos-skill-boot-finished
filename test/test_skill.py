import unittest
from threading import Event
from unittest.mock import Mock

from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus

from ovos_skill_boot_finished import BootFinishedSkill


class TestSkill(unittest.TestCase):
    bus = FakeBus()
    bus.emitter = bus.ee
    bus.connected_event = Event()
    bus.connected_event.set()
    bus.run_forever()
    skill_id = "ovos-skill-boot-finished.openvoiceos"

    @classmethod
    def setUpClass(cls):
        cls.skill = BootFinishedSkill()
        cls.skill._startup(cls.bus, cls.skill_id)
        cls.skill.speak = Mock()
        cls.skill.speak_dialog = Mock()

    def setUp(self):
        self.skill.speak.reset_mock()
        self.skill.speak_dialog.reset_mock()

    def test_skill_init(self):
        self.assertGreaterEqual(
            len(self.skill.bus.ee.listeners("mycroft.ready")), 1)
        self.assertTrue(self.skill.speak_ready)

    def test_handle_enable_notification(self):
        self.skill.settings['speak_ready'] = False
        self.skill.handle_enable_notification(Message(""))
        self.assertTrue(self.skill.speak_ready)
        self.skill.speak_dialog.assert_called_once_with("confirm_speak_ready")

    def test_handle_disable_notification(self):
        self.skill.settings['speak_ready'] = True
        self.skill.handle_disable_notification(Message(""))
        self.assertFalse(self.skill.speak_ready)
        self.skill.speak_dialog.assert_called_once_with(
            "confirm_no_speak_ready")
