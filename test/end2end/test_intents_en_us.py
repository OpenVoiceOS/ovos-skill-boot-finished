"""End-to-end intent tests for the en-US locale.

Each canonical utterance is fired through a real MiniCroft. It must route to
the expected intent handler, and the handler must speak a line of that
intent's own ``.dialog`` file. The expected lines are read from the locale
files on disk, so a handler that speaks the dialog of another intent fails
even though it still matched and still spoke. The enable and disable
handlers must also set the ``speak_ready`` setting.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession
from ovoscope.routing import PIPELINE, TALLY, get_prototype_minicroft

SKILL_ID = "ovos-skill-boot-finished.openvoiceos"
LANG = "en-US"
DIALOG_DIR = Path(__file__).parents[2] / "locale" / LANG / "dialog"
DIALOGS = ("confirm_ready", "deny_ready", "confirm_speak_ready",
           "confirm_no_speak_ready", "ready")


def _dialog_lines(name: str) -> set:
    path = DIALOG_DIR / f"{name}.dialog"
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()}


# is_device_ready() is patched to True, so are_you_ready speaks confirm_ready
INTENT_DIALOG = {
    "are_you_ready.intent": "confirm_ready",
    "enable_ready_notification.intent": "confirm_speak_ready",
    "disable_ready_notification.intent": "confirm_no_speak_ready",
}
INTENT_SETTING = {
    "enable_ready_notification.intent": True,
    "disable_ready_notification.intent": False,
}


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
        cls.minicroft = get_prototype_minicroft([SKILL_ID], lang=LANG)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "minicroft", None):
            cls.minicroft.stop()
        cls._ready_patch.stop()

    def _run(self, text):
        session = Session("test-session")
        session.lang = LANG
        session.pipeline = PIPELINE
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(self.minicroft)
        capture.capture(utterance, timeout=30)
        return capture.finish()

    def _assert_intent(self, text, intent):
        skill = self.minicroft.plugin_skills[SKILL_ID].instance
        # the opposite value, so a handler that leaves the setting alone fails
        if intent in INTENT_SETTING:
            skill.settings["speak_ready"] = not INTENT_SETTING[intent]
        messages = self._run(text)
        types = [m.msg_type for m in messages]
        TALLY.assert_routed(text, f"{SKILL_ID}:{intent}", types)
        spoken = [m.data.get("utterance", "") for m in messages
                  if m.msg_type in ("speak", "ovos.utterance.speak")]
        expected = _dialog_lines(INTENT_DIALOG[intent])
        self.assertTrue(any(line in expected for line in spoken),
                        f"{text!r}: expected a line of {INTENT_DIALOG[intent]}.dialog, "
                        f"got {spoken!r}")
        if intent in INTENT_SETTING:
            self.assertEqual(skill.settings["speak_ready"], INTENT_SETTING[intent], text)

    def test_dialog_files_share_no_line(self):
        """A shared line would let a handler speak the wrong dialog and pass."""
        lines = {name: _dialog_lines(name) for name in DIALOGS}
        for i, first in enumerate(DIALOGS):
            for second in DIALOGS[i + 1:]:
                self.assertFalse(lines[first] & lines[second], (first, second))

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
