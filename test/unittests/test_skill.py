import os
import tempfile
import unittest
from threading import Event
from unittest.mock import Mock, patch

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
        # Private XDG tree: the skill settings come from a clean file, not
        # from the settings of the user who runs the tests.
        xdg = tempfile.TemporaryDirectory()
        cls.addClassCleanup(xdg.cleanup)
        env = {var: os.path.join(xdg.name, var.lower()) for var in (
            "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME")}
        env_patch = patch.dict(os.environ, env)
        env_patch.start()
        cls.addClassCleanup(env_patch.stop)

        # initialize() emits mycroft.ready.check, which FakeBus delivers
        # synchronously. The real handler polls the services for up to 60s
        # and then re-emits the check forever, so it must not run here.
        with patch.object(BootFinishedSkill, "handle_check_device_readiness",
                          lambda self, message=None: None):
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
