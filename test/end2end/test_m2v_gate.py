"""m2v-multilingual candidate-default gate for ovos-skill-boot-finished.

Boots the skill through the candidate default intent engine -- the
model2vec multilingual classifier (``OpenVoiceOS/ovos-m2v-intents-multi-128M-v5``)
-- via ovoscope's ``get_m2v_minicroft`` and asserts, for a representative
slice of the skill's own golden utterances, the whole round trip: the
correct intent routed AND the rendered speech carries the real
confirmation/denial wording, not the raw dialog file name.

``is_device_ready()`` polls every other loaded service for a ready signal
and blocks for up to 60s in a minimal MiniCroft; readiness gating is not
under test here (intent routing is), so it is short-circuited to ``True``
the same way ``test/end2end/test_golden_utterances.py`` does for the
padacioso suite.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session

from ovoscope import get_m2v_minicroft, M2V_PIPELINE

SKILL_ID = "ovos-skill-boot-finished.openvoiceos"
LANG = "en-US"

_MC = None
_PIPE = None
_XDG = None
_ORIG_XDG = None
_READY_PATCH = None


def setUpModule():
    global _MC, _PIPE, _XDG, _ORIG_XDG, _READY_PATCH
    _ORIG_XDG = os.environ.get("XDG_DATA_HOME")
    _XDG = tempfile.mkdtemp(prefix="ovoscope-m2v-boot-finished-xdg-")
    os.environ["XDG_DATA_HOME"] = _XDG

    _READY_PATCH = patch(
        "ovos_skill_boot_finished.BootFinishedSkill.is_device_ready",
        new=lambda self, *args, **kwargs: True,
    )
    _READY_PATCH.start()

    _MC = get_m2v_minicroft(skill_ids=[SKILL_ID], lang=LANG)
    _PIPE = _MC.intents.pipeline_plugins["ovos-m2v-pipeline"]
    _PIPE._ensure_model(background_ok=False)


def tearDownModule():
    global _MC, _XDG, _ORIG_XDG, _READY_PATCH
    if _MC is not None:
        _MC.stop()
        _MC = None
    if _READY_PATCH is not None:
        _READY_PATCH.stop()
        _READY_PATCH = None
    if _ORIG_XDG is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = _ORIG_XDG
    if _XDG is not None:
        shutil.rmtree(_XDG, ignore_errors=True)
        _XDG = None


class TestM2VBootFinishedGoldenEffect(unittest.TestCase):
    """Effect assertions: golden utterance in -> correct intent -> real confirmation spoken."""

    def _run(self, utterance: str, lang: str = LANG, timeout: float = 15.0):
        speaks = []
        failures = []

        def _on_speak(msg):
            speaks.append(msg)

        def _on_fail(msg):
            failures.append(msg)

        _MC.bus.on("speak", _on_speak)
        _MC.bus.on("complete_intent_failure", _on_fail)
        sess = Session(session_id=f"m2v-golden-{hash(utterance)}", pipeline=M2V_PIPELINE)
        sess.lang = lang
        try:
            _MC.bus.emit(Message(
                "recognizer_loop:utterance",
                data={"utterances": [utterance], "lang": lang},
                context={"session": sess.serialize(), "lang": lang},
            ))
            import time as _t
            deadline = _t.time() + timeout
            while _t.time() < deadline and not speaks and not failures:
                _t.sleep(0.05)
        finally:
            _MC.bus.remove("speak", _on_speak)
            _MC.bus.remove("complete_intent_failure", _on_fail)

        if not speaks:
            return None, None, bool(failures)
        data = speaks[0].data
        meta = data.get("meta", {}) or {}
        return meta.get("dialog"), (data.get("utterance") or ""), False

    def _assert_effect(self, utterance, expected_dialog, expected_substrings):
        dialog, text, failed = self._run(utterance)
        self.assertFalse(failed, f"{utterance!r} did not route: complete_intent_failure")
        self.assertIsNotNone(text, f"{utterance!r} produced no spoken output")
        low = text.lower()
        self.assertEqual(
            dialog, expected_dialog,
            f"{utterance!r} routed to dialog {dialog!r}, expected {expected_dialog!r} "
            f"(rendered: {text!r})")
        self.assertNotIn(
            dialog, low,
            f"{utterance!r} spoke the dialog NAME, not rendered text: {text!r}")
        self.assertTrue(
            any(sub in low for sub in expected_substrings),
            f"{utterance!r} rendered {text!r}; missing any of {expected_substrings!r}")

    def test_has_ovos_boot_successfully(self):
        # is_device_ready() patched True -> confirm_ready.
        self._assert_effect(
            "Has Open Voice OS boot successfully", "confirm_ready",
            ["ready", "operational", "up and running"])

    def test_did_the_system_boot_successfully(self):
        self._assert_effect(
            "did the system boot successfully", "confirm_ready",
            ["ready", "operational", "up and running"])

    def test_enable_ready_notifications(self):
        self._assert_effect(
            "enable ready notifications", "confirm_speak_ready",
            ["tell you", "notify", "notif"])

    def test_turn_on_boot_notification(self):
        self._assert_effect(
            "turn on boot notification", "confirm_speak_ready",
            ["tell you", "notify", "notif"])

    def test_disable_readiness_sounds(self):
        self._assert_effect(
            "disable readiness sounds", "confirm_no_speak_ready",
            ["stop", "will not", "won't"])


class TestM2VRegisteredLabelRouting(unittest.TestCase):
    """The model's labels carry the skill's real runtime id and route it."""

    def test_registered_skill_id_labels_route(self):
        classes = {str(c) for c in _PIPE.model.classes_}
        registered = set(_PIPE.intents)
        self.assertIn(f"{SKILL_ID}:are_you_ready", registered)
        self.assertTrue(
            registered & classes,
            "registered intent labels do not intersect the model's classes; "
            f"{SKILL_ID} would route nothing through this model")


if __name__ == "__main__":
    unittest.main()
