"""Golden-utterance end-to-end coverage for ovos-skill-boot-finished (en-US).

The golden corpus (``golden_utterances.jsonl``) is a vendored slice of the
shared ovoscope golden-utterance dataset, keyed by
``skill_id == "ovos-skill-boot-finished.openvoiceos"``. One shared
``MiniCroft`` (module-scoped fixture) is booted for the whole suite; every
row is its own parametrized test item.

Dispatched ``ovos.intent.matched`` intent names carry no ``.intent`` suffix
(OVOS-INTENT-2 naming) even though the golden corpus's ``intent_label``
field still stores the on-disk container filename -- the suffix is stripped
before comparison, matching the fix applied to ``test_intents_en_us.py``.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-boot-finished.openvoiceos"
LANG = "en-US"

GOLDEN_PATH = Path(__file__).parent / "golden_utterances.jsonl"

# utterances lifted verbatim from OTHER skills' golden-utterance slices,
# picked for lexical overlap with boot-finished's "ready"/"notification"/
# "enable"/"disable" vocabulary.
NEGATIVE_UTTERANCES = [
    ("what color is this", "ovos-skill-color-picker.openvoiceos"),
    ("take a picture", "ovos-skill-camera.openvoiceos"),
    ("count to ten", "ovos-skill-count.openvoiceos"),
    ("what happened today in history", "ovos-skill-days-in-history.openvoiceos"),
    ("launch spotify", "ovos-skill-application-launcher.openvoiceos"),
    ("set a timer for 5 minutes", "ovos-skill-alerts.openvoiceos"),
    ("turn off the lights", "ovos-skill-homeassistant.openvoiceos"),
]


def _label_to_bus_name(intent_label: str) -> str:
    return intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label


def _load_golden_rows():
    rows = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


GOLDEN_ROWS = [pytest.param(r, id=r["utterance"]) for r in _load_golden_rows()]


@pytest.fixture(scope="module")
def minicroft():
    # is_device_ready() polls every other loaded service for a ready signal
    # and blocks for 60s in a minimal MiniCroft -- short-circuit it so the
    # skill boots deterministically (readiness gating is not under test
    # here, intent routing is; see test_intents_en_us.py for the full
    # rationale).
    ready_patch = patch(
        "ovos_skill_boot_finished.BootFinishedSkill.is_device_ready",
        new=lambda self, *args, **kwargs: True,
    )
    ready_patch.start()
    mc = get_minicroft([SKILL_ID])
    yield mc
    mc.stop()
    ready_patch.stop()


def _types(mc, text, session_id):
    session = Session(session_id)
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
    capture = CaptureSession(mc)
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=lambda r: r["utterance"])
def test_golden_utterance(minicroft, row):
    intent_name = _label_to_bus_name(row["intent_label"])
    types = _types(minicroft, row["utterance"], f"golden-{row['utterance']}")
    assert f"{SKILL_ID}:{intent_name}" in types, (
        f"{row['utterance']!r}: expected {SKILL_ID}:{intent_name!r}, got {types!r}"
    )


@pytest.mark.timeout(60)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicroft, negative):
    text, source_skill = negative
    types = _types(minicroft, text, f"negative-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
