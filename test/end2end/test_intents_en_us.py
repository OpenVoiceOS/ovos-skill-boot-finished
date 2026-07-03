"""End-to-end intent routing tests for the en-US locale.

Each canonical utterance is fired through a real MiniCroft and asserted to
route to the expected intent handler and produce a spoken response. Assertions
cover the intent binding and the presence of a ``speak`` response.
"""
import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-boot-finished.openvoiceos"
LANG = "en-US"


class TestBootFinishedIntentsEnUS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This skill gates device readiness: is_device_ready() polls every other
        # loaded service for a ready signal and blocks for 60s in a minimal
        # MiniCroft, where no such services report in. Readiness gating is not
        # the unit under test -- intent routing is -- so it is short-circuited so
        # the skill emits mycroft.ready and MiniCroft boots deterministically.
        cls._ready_patch = patch(
            "ovos_skill_boot_finished.BootFinishedSkill.is_device_ready",
            new=lambda self, *args, **kwargs: True,
        )
        cls._ready_patch.start()
        cls.minicroft = get_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()
        cls._ready_patch.stop()

    def _run(self, text):
        session = Session("test-session")
        session.lang = LANG
        session.pipeline = [
            "ovos-padacioso-pipeline-plugin-high",
            "ovos-padacioso-pipeline-plugin-medium",
        ]
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(self.minicroft)
        capture.capture(utterance, timeout=30)
        return capture.finish()

    def _assert_intent(self, text, intent):
        messages = self._run(text)
        types = [m.msg_type for m in messages]
        self.assertIn(f"{SKILL_ID}:{intent}", types)
        self.assertTrue(any("speak" in t for t in types))

    def test_are_you_ready(self):
        self._assert_intent("are you ready", "are_you_ready.intent")

    def test_is_the_system_ready(self):
        self._assert_intent("is the system ready", "are_you_ready.intent")

    def test_have_you_finished_booting(self):
        self._assert_intent("have you finished booting", "are_you_ready.intent")

    def test_enable_ready_notifications(self):
        self._assert_intent("enable ready notifications", "enable_ready_notification.intent")

    def test_turn_on_boot_notification(self):
        self._assert_intent("turn on boot notification", "enable_ready_notification.intent")

    def test_disable_readiness_sounds(self):
        self._assert_intent("disable readiness sounds", "disable_ready_notification.intent")

    def test_turn_off_load_sound(self):
        self._assert_intent("turn off load sound", "disable_ready_notification.intent")
