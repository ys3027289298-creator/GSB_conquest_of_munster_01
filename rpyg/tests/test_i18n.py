"""Traductions : repli sur la langue de secours, clés manquantes."""
import json

import pytest

from core.game.I18n import Translation


@pytest.fixture
def lang_dir(tmp_path):
    (tmp_path / "en.json").write_text(
        json.dumps({"ui": {"hello": "Hello", "heal": "+{amount} HP"}}),
        encoding="utf-8",
    )
    (tmp_path / "fr.json").write_text(
        json.dumps({"ui": {"hello": "Bonjour"}}),
        encoding="utf-8",
    )
    return tmp_path


def test_missing_locale_file_falls_back(lang_dir):
    t = Translation(locales="de", locales_dir=lang_dir)
    assert t.t("ui.hello") == "Hello"


def test_corrupt_locale_file_falls_back(lang_dir):
    (lang_dir / "de.json").write_text("{pas du json", encoding="utf-8")
    t = Translation(locales="de", locales_dir=lang_dir)
    assert t.t("ui.hello") == "Hello"


def test_missing_fallback_file_does_not_crash(tmp_path):
    (tmp_path / "fr.json").write_text(json.dumps({"a": "b"}), encoding="utf-8")
    t = Translation(locales="zz", locales_dir=tmp_path, fallback="missing")
    assert t.t("a") == "a"


def test_locale_overrides_fallback(lang_dir):
    t = Translation(locales="fr", locales_dir=lang_dir)
    assert t.t("ui.hello") == "Bonjour"


def test_missing_key_in_locale_uses_fallback(lang_dir):
    t = Translation(locales="fr", locales_dir=lang_dir)
    assert t.t("ui.heal", amount=3) == "+3 HP"


def test_unknown_key_returns_the_key(lang_dir):
    t = Translation(locales="en", locales_dir=lang_dir)
    assert t.t("ui.nope") == "ui.nope"


def test_missing_format_param_returns_raw_text(lang_dir):
    t = Translation(locales="en", locales_dir=lang_dir)
    assert t.t("ui.heal") == "+{amount} HP"


def test_has_checks_locale_and_fallback(lang_dir):
    t = Translation(locales="fr", locales_dir=lang_dir)
    assert t.has("ui.hello") is True
    assert t.has("ui.heal") is True
    assert t.has("ui.nope") is False


def test_shipped_french_locale_loads():
    from pathlib import Path
    lang = Path(__file__).resolve().parents[1] / "data" / "lang"
    t = Translation(locales="fr", locales_dir=lang)
    assert t.t("ui.bindings.explore")
    assert t.t("ui.bindings.quit")
