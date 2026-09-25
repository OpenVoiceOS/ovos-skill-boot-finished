"""End-to-end intent routing tests for the en-US locale.

Each canonical utterance is fired through a real MiniCroft and asserted to
route to the expected intent handler AND to speak a dialog line drawn from
that intent's own ``.dialog`` file. The expected line set is read directly
from the locale file on disk, independent of the skill handler under test,
so a handler that speaks the wrong dialog (or the right dialog for a
different intent) fails here even though it still emits a ``speak`` message
and still matches the correct intent name.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-boot-finished.openvoiceos"
LANG = "en-US"
LOCALE_EN_US = Path(__file__).parent.parent.parent / "locale" / "en-US"


def _dialog_lines(name: str) -> set:
    """Read dialog lines from disk at test time, independent of the handler."""
    path = LOCALE_EN_US / "dialog" / f"{name}.dialog"
    with open(path, encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}


# Read once, directly from the shipped dialog files -- never from a captured
# bus message -- so these sets are independent of the code under test.
CONFIRM_READY_LINES = _dialog_lines("confirm_ready")
DENY_READY_LINES = _dialog_lines("deny_ready")
CONFIRM_SPEAK_READY_LINES = _dialog_lines("confirm_speak_ready")
CONFIRM_NO_SPEAK_READY_LINES = _dialog_lines("confirm_no_speak_ready")
READY_LINES = _dialog_lines("ready")

_DIALOG_LINES = {
    "are_you_ready": CONFIRM_READY_LINES,
    "enable_ready_notification": CONFIRM_SPEAK_READY_LINES,
    "disable_ready_notification": CONFIRM_NO_SPEAK_READY_LINES,
}

# Test that dialog files are pairwise disjoint: speaking the wrong dialog
# must fail even if the intent matched and some speak message was emitted.
_ALL_DIALOG_LINES = (
    CONFIRM_READY_LINES,
    DENY_READY_LINES,
    CONFIRM_SPEAK_READY_LINES,
    CONFIRM_NO_SPEAK_READY_LINES,
    READY_LINES,
)


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
        """Assert the utterance matched the intent and spoke the expected dialog."""
        # dispatched ovos.intent.matched intent names carry no ".intent"
        # suffix (OVOS-INTENT-2 naming) -- strip it so this assertion tracks
        # the real bus event instead of the on-disk container filename.
        intent_name = intent[:-len(".intent")] if intent.endswith(".intent") else intent
        messages = self._run(text)
        types = [m.msg_type for m in messages]
        self.assertIn(f"{SKILL_ID}:{intent_name}", types)
        
        # Extract spoken utterances from speak messages.
        spoken = [
            m.data.get("utterance", "")
            for m in messages
            if m.msg_type in ("speak", "ovos.utterance.speak")
        ]
        self.assertTrue(spoken, f"expected a spoken response for {text!r}, got {types!r}")
        
        # Assert the spoken line is from this intent's own dialog file, not from
        # another intent's dialog or an untranslated identifier.
        expected_lines = _DIALOG_LINES[intent_name]
        self.assertTrue(
            any(utt in expected_lines for utt in spoken),
            f"expected one of {intent_name}.dialog's own lines to be spoken for "
            f"{text!r}, got {spoken!r}",
        )

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

    def test_dialog_disjointness(self):
        """Assert that dialog files are pairwise disjoint so speaking the wrong dialog fails."""
        for i, set_a in enumerate(_ALL_DIALOG_LINES):
            for set_b in _ALL_DIALOG_LINES[i + 1 :]:
                shared = set_a & set_b
                self.assertFalse(
                    shared,
                    f"dialog files share lines: {shared!r}. "
                    f"A handler speaking the wrong dialog would pass without detecting it.",
                )
