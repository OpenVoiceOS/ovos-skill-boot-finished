"""Multilingual golden-utterance end-to-end coverage for
ovos-skill-boot-finished.

test_golden_utterances.py only exercises en-US; every other locale under
locale/ that ships all three .intent files (are_you_ready,
enable_ready_notification, disable_ready_notification) had no end-to-end
coverage. locale/kab ships only a ready.dialog and skill.json, no .intent
content, so it is not covered here.

Dispatched ovos.intent.matched intent names carry no .intent suffix
(OVOS-INTENT-2 naming) even though the golden corpus's intent_label field
still stores the on-disk container filename, matching the convention
test_golden_utterances.py already uses for en-US.

One MiniCroft is booted PER LOCALE (module-scoped fixture, indirectly
parametrized by lang; pytest reuses one boot per distinct lang value
across every row of that lang and tears it down before moving on).

Row construction: each row is derived mechanically from that locale's own
.intent template lines (its own bracket-alternation choices), never a
translation of the English rows.
"""
import json
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-boot-finished.openvoiceos"

END2END_DIR = Path(__file__).parent

LANGS = [
    "en-US", "ca-ES", "da-DK", "de-DE", "es-ES", "eu-ES", "fr-FR",
    "gl-ES", "it-IT", "nl-NL", "pt-BR", "pt-PT", "sv-SE",
]


def _label_to_bus_name(intent_label: str) -> str:
    return intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label


def _load_rows(lang):
    path = END2END_DIR / f"golden_utterances_{lang}.jsonl"
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


ALL_ROWS = []
for _lang in LANGS:
    for _row in _load_rows(_lang):
        ALL_ROWS.append(_row)


def _golden_id(row):
    return f"{row['lang']}-{row['intent_label']}-{row['utterance']}"


@pytest.fixture(scope="module")
def minicroft(request):
    """One MiniCroft boot per distinct lang value, reused across every row
    of that lang."""
    lang = request.param
    ready_patch = patch(
        "ovos_skill_boot_finished.BootFinishedSkill.is_device_ready",
        new=lambda self, *args, **kwargs: True,
    )
    ready_patch.start()
    # padatious training (fann/numpy) is heavy and its background training
    # thread is not cancelled by pytest-timeout, so a slow/contended box can
    # hang the whole suite well past any per-test timeout. This suite only
    # ever queries via padacioso, so keep padatious out of the boot entirely.
    mc = get_minicroft(
        [SKILL_ID], max_wait=150, lang=lang,
        default_pipeline=[
            "ovos-padacioso-pipeline-plugin-high",
            "ovos-padacioso-pipeline-plugin-medium",
        ],
    )
    yield mc
    mc.stop()
    ready_patch.stop()


def _types(mc, text, lang, session_id) -> List[str]:
    session = Session(session_id)
    session.lang = lang
    session.pipeline = [
        "ovos-padacioso-pipeline-plugin-high",
        "ovos-padacioso-pipeline-plugin-medium",
    ]
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(mc)
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


KNOWN_BUGS = {}

_PARAMS = [
    pytest.param(row["lang"], row, id=_golden_id(row))
    for row in ALL_ROWS
]


@pytest.mark.timeout(300)
@pytest.mark.parametrize("minicroft,row", _PARAMS, indirect=["minicroft"])
def test_golden_utterance_multilang(minicroft, row):
    intent_name = _label_to_bus_name(row["intent_label"])
    types = _types(minicroft, row["utterance"], row["lang"], f"golden-{_golden_id(row)}")
    matched = f"{SKILL_ID}:{intent_name}" in types
    bug_key = (row["lang"], row["utterance"])
    if bug_key in KNOWN_BUGS and not matched:
        pytest.xfail(reason=f"known-bug: {KNOWN_BUGS[bug_key]}")
    assert matched, (
        f"[{row['lang']}] {row['utterance']!r}: expected {SKILL_ID}:{intent_name!r}, got {types!r}"
    )
