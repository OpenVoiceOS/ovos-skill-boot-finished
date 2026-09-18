"""Locale-parity coverage: every dialog a handler can speak must exist in
every locale that ships the intent driving it, or the renderer speaks the
literal dialog key aloud instead of falling back silently.
"""
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent.parent
LOCALE_ROOT = SKILL_ROOT / "locale"

# every "name" passed to self.speak_dialog("name") in __init__.py, associated
# with the intent whose handler reaches it.
HANDLER_DIALOGS = {
    "are_you_ready.intent": ["confirm_ready", "deny_ready"],
    "enable_ready_notification.intent": ["confirm_speak_ready"],
    "disable_ready_notification.intent": ["confirm_no_speak_ready"],
}


def _extract_speak_dialog_names():
    src = (SKILL_ROOT / "__init__.py").read_text(encoding="utf-8")
    return set(re.findall(r'speak_dialog\("([^"]+)"\)', src))


def test_handler_dialog_map_is_complete():
    # guards HANDLER_DIALOGS itself against drift from the source file
    found = _extract_speak_dialog_names()
    mapped = {name for names in HANDLER_DIALOGS.values() for name in names}
    mapped.add("ready")  # spoken from handle_ready, not an intent handler
    assert found == mapped, (
        f"__init__.py speak_dialog() calls {found} do not match the "
        f"dialogs this test tracks {mapped}"
    )


def test_every_locale_can_speak_every_dialog_its_intents_reach():
    missing = {}
    for locale_dir in sorted(LOCALE_ROOT.iterdir()):
        if not locale_dir.is_dir():
            continue
        intent_dir = locale_dir / "intent"
        dialog_dir = locale_dir / "dialog"
        shipped_intents = (
            {p.name for p in intent_dir.iterdir()} if intent_dir.is_dir() else set()
        )
        shipped_dialogs = (
            {p.stem for p in dialog_dir.iterdir()} if dialog_dir.is_dir() else set()
        )
        for intent_file, dialog_names in HANDLER_DIALOGS.items():
            if intent_file not in shipped_intents:
                continue
            for dialog_name in dialog_names:
                if dialog_name not in shipped_dialogs:
                    missing.setdefault(locale_dir.name, []).append(
                        f"{dialog_name}.dialog (reached by {intent_file})"
                    )
    assert not missing, (
        "locales ship an intent whose handler speaks a dialog that does not "
        f"exist for that locale, so the renderer speaks the literal key: {missing}"
    )
