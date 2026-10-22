"""Each ready-notification intent is closed to the other one's sentences.

A locale's `enable` and `disable` templates share most of their words, so the
classifier cannot tell them apart. The `.blacklist` of one intent holds the
phrases of its opposite, and OVOS-INTENT-2 section 4.3 drops an intent when a
blacklist phrase occurs in the utterance as whole words.
"""
from pathlib import Path

import pytest
from ovos_spec_tools.expansion import expand
from ovos_spec_tools.resources import read_resource_file, utterance_contains

LOCALE = Path(__file__).resolve().parents[1] / "locale"
LANGS = sorted(p.parent.parent.name
               for p in LOCALE.glob("*/intent/enable_ready_notification.blacklist"))
SAMPLES_PER_LINE = 40


def _blacklist(lang, name):
    return read_resource_file(LOCALE / lang / "intent" / f"{name}_ready_notification.blacklist")


def _sentences(lang, name):
    out = []
    for line in read_resource_file(LOCALE / lang / "intent" / f"{name}_ready_notification.intent"):
        expansions = expand(line)
        step = max(len(expansions) // SAMPLES_PER_LINE, 1)
        out.extend(expansions[::step])
    return out


def _opens(blacklist, sentence):
    return not utterance_contains(sentence, blacklist)


def test_every_locale_with_templates_has_both_blacklists():
    with_enable = {p.parent.parent.name
                   for p in LOCALE.glob("*/intent/enable_ready_notification.intent")}
    with_disable = {p.parent.parent.name
                    for p in LOCALE.glob("*/intent/disable_ready_notification.intent")}
    assert with_enable == with_disable == set(LANGS)
    assert set(LANGS) == {p.parent.parent.name
                          for p in LOCALE.glob("*/intent/disable_ready_notification.blacklist")}


@pytest.mark.parametrize("lang", LANGS)
def test_an_enable_sentence_reaches_enable_only(lang):
    for sentence in _sentences(lang, "enable"):
        assert _opens(_blacklist(lang, "enable"), sentence), sentence
        assert not _opens(_blacklist(lang, "disable"), sentence), sentence


@pytest.mark.parametrize("lang", LANGS)
def test_a_disable_sentence_reaches_disable_only(lang):
    for sentence in _sentences(lang, "disable"):
        assert _opens(_blacklist(lang, "disable"), sentence), sentence
        assert not _opens(_blacklist(lang, "enable"), sentence), sentence


@pytest.mark.parametrize("disable_word", [
    "غیرفعال",
    "غیر فعال",
    "غیر‌فعال",
])
def test_every_persian_spelling_of_disable_reaches_disable_only(disable_word):
    sentence = f"صدای آماده را {disable_word} کنید"
    assert _opens(_blacklist("fa-IR", "disable"), sentence)
    assert not _opens(_blacklist("fa-IR", "enable"), sentence)


def test_persian_enable_reaches_enable_only():
    sentence = "صدای آماده را فعال کنید"
    assert _opens(_blacklist("fa-IR", "enable"), sentence)
    assert not _opens(_blacklist("fa-IR", "disable"), sentence)
