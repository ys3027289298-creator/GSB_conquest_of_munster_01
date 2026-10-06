"""Les données livrées (monde + traductions) sont cohérentes et complètes."""
from pathlib import Path

import pytest

from core.game.I18n import Translation
from core.world.models import RoomRef
from core.world.loader import load_world

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LANG_DIR = DATA_DIR / "lang"
LOCALES = ["en", "fr", "de", "es"]

# Clés effectivement utilisées par les écrans au runtime.
REQUIRED_UI_KEYS = [
    "ui.main_menu.title", "ui.main_menu.new_game", "ui.main_menu.load_game",
    "ui.main_menu.quit", "ui.main_menu.options", "ui.main_menu.lore",
    "ui.main_menu.tagline", "ui.main_menu.version",
    "ui.common.back", "ui.common.invalid_choice", "ui.common.level",
    "ui.common.quit", "ui.common.unavailable",
    "ui.creation.title", "ui.creation.name", "ui.creation.name_prompt",
    "ui.creation.points_left", "ui.creation.set_name", "ui.creation.confirm",
    "ui.exploration.look_around", "ui.exploration.save_game",
    "ui.exploration.back_to_menu", "ui.exploration.navigation",
    "ui.slots.title_load", "ui.slots.title_save", "ui.slots.empty",
    "ui.slots.unreadable",
    "ui.options.title", "ui.options.language",
    "ui.stats.health", "ui.stats.strength", "ui.stats.speed", "ui.stats.luck",
    "ui.stats.abrev.health",
    "ui.directions.north", "ui.directions.south", "ui.directions.east",
    "ui.directions.west",
    "ui.messages.already_explored", "ui.messages.nothing_special",
    "ui.messages.game_saved", "ui.messages.save_failed",
    "ui.messages.game_loaded", "ui.messages.invalid_save",
    "ui.messages.healed", "ui.messages.already_full_health",
    "ui.presence.main_menu", "ui.presence.creation", "ui.presence.exploring",
    "ui.presence.level", "ui.bindings.explore", "ui.bindings.quit",
]


@pytest.fixture(scope="module")
def shipped_world():
    return load_world(DATA_DIR)


def test_shipped_world_loads(shipped_world):
    assert shipped_world.start is not None


def test_start_room_exists(shipped_world):
    shipped_world.get_room(shipped_world.start)


def test_shipped_exits_target_existing_rooms(shipped_world):
    for zone in shipped_world.zones.values():
        for room in zone.rooms.values():
            for target in room.exits.values():
                shipped_world.get_room(target)


def test_shipped_world_has_no_unreachable_room(shipped_world):
    seen = set()
    frontier = [shipped_world.start]
    while frontier:
        ref = frontier.pop()
        if ref in seen:
            continue
        seen.add(ref)
        frontier.extend(shipped_world.get_room(ref).exits.values())

    expected = {
        RoomRef(zone.id, room_id)
        for zone in shipped_world.zones.values()
        for room_id in zone.rooms
    }
    assert seen == expected


@pytest.mark.parametrize("locale", LOCALES)
def test_all_ui_keys_are_translated(locale):
    translations = Translation(locales=locale, locales_dir=LANG_DIR).translations
    missing = [key for key in REQUIRED_UI_KEYS if key not in translations]
    assert missing == []


@pytest.mark.parametrize("locale", LOCALES)
def test_all_shipped_rooms_are_translated(locale, shipped_world):
    translations = Translation(locales=locale, locales_dir=LANG_DIR).translations
    for zone in shipped_world.zones.values():
        assert f"zones.{zone.id}.name" in translations
        assert f"zones.{zone.id}.description" in translations
        for room_id, room in zone.rooms.items():
            base = f"zones.{zone.id}.rooms.{room_id}"
            assert f"{base}.name" in translations
            assert f"{base}.description" in translations
            if room.look_around:
                assert f"{base}.look_around" in translations
