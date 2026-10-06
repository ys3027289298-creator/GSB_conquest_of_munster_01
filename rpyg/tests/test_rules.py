"""Règles de jeu : exploration, cycle de vie d'une partie, actions répétées."""
import pytest

from core.enums import Direction, Screens, Stat
from core.game.actions import (
    AllocatePoints, ConfirmCreation, Explore, Move, NewGame, Quit, SetName,
)
from core.game.rules import CREATION_POINTS, STAT_RULES
from core.game.text_keys import room_key
from core.world.models import RoomRef


@pytest.fixture
def game_exploring(game_in_creation):
    game_in_creation.handle_action(SetName("Bob"))
    game_in_creation.handle_action(ConfirmCreation())
    return game_in_creation


# --- Exploration : premier regard vs déjà exploré ----------------------------

def test_first_explore_shows_look_around(game_exploring):
    response = game_exploring.handle_action(Explore())
    keys = [m.key for m in response.messages]
    assert "ui.messages.already_explored" not in keys
    assert room_key(game_exploring.player.location, "look_around") in keys


def test_first_explore_marks_room_as_explored(game_exploring):
    ref = game_exploring.player.location
    assert ref not in game_exploring.world_state.explored
    game_exploring.handle_action(Explore())
    assert ref in game_exploring.world_state.explored


def test_second_explore_says_already_explored(game_exploring):
    game_exploring.handle_action(Explore())
    response = game_exploring.handle_action(Explore())
    keys = [m.key for m in response.messages]
    assert "ui.messages.already_explored" in keys


def test_explore_only_marks_current_room(game_exploring):
    game_exploring.handle_action(Explore())
    game_exploring.handle_action(Move(Direction.SOUTH))
    ref = game_exploring.player.location
    assert ref not in game_exploring.world_state.explored
    response = game_exploring.handle_action(Explore())
    keys = [m.key for m in response.messages]
    assert "ui.messages.already_explored" not in keys
    assert ref in game_exploring.world_state.explored


def test_room_without_look_around_uses_fallback(game_exploring):
    # La porte du village n'a pas de texte "look_around" : message de repli.
    game_exploring.handle_action(Move(Direction.SOUTH))
    response = game_exploring.handle_action(Explore())
    message = response.messages[-1]
    assert message.key == room_key(game_exploring.player.location, "look_around")
    assert message.fallback_key == "ui.messages.nothing_special"


# --- Confirmation en double ---------------------------------------------------

def test_double_confirm_creation_does_not_crash(game_exploring):
    # Un double-clic sur "Confirmer" ne doit pas faire planter le jeu.
    response = game_exploring.handle_action(ConfirmCreation())
    assert response.screen is Screens.EXPLORATION
    assert game_exploring.player is not None
    assert game_exploring.player.name == "Bob"


def test_double_confirm_keeps_single_player(game_exploring):
    player = game_exploring.player
    game_exploring.handle_action(ConfirmCreation())
    assert game_exploring.player is player


# --- Recommencer une partie ---------------------------------------------------

def test_new_game_resets_player(game_exploring):
    game_exploring.handle_action(Quit())
    game_exploring.handle_action(NewGame())
    assert game_exploring.player is None


def test_new_game_resets_explored_rooms(game_exploring):
    game_exploring.handle_action(Explore())
    game_exploring.handle_action(Move(Direction.SOUTH))
    game_exploring.handle_action(Explore())
    assert game_exploring.world_state.explored

    game_exploring.handle_action(Quit())
    game_exploring.handle_action(NewGame())
    assert game_exploring.world_state.explored == set()


def test_recreated_character_starts_without_explored_rooms(game_exploring):
    game_exploring.handle_action(Explore())
    game_exploring.handle_action(Quit())
    game_exploring.handle_action(NewGame())
    game_exploring.handle_action(SetName("Ann"))
    game_exploring.handle_action(ConfirmCreation())

    assert game_exploring.player.name == "Ann"
    assert game_exploring.world_state.explored == set()
    response = game_exploring.handle_action(Explore())
    keys = [m.key for m in response.messages]
    assert "ui.messages.already_explored" not in keys


# --- Règles de stats (rappel des invariants) ----------------------------------

def test_stat_rules_cover_all_stats():
    for stat in Stat:
        assert stat in STAT_RULES


def test_stat_values_combine_base_points_and_level(game_exploring):
    player = game_exploring.player
    player.allocated_points[Stat.STRENGTH] = 3
    rule = STAT_RULES[Stat.STRENGTH]
    assert player.get_stat(Stat.STRENGTH) == rule.base + 3 * rule.per_point
    player.level = 4
    assert player.get_stat(Stat.STRENGTH) == (
        rule.base + 3 * rule.per_point + 3 * rule.growth_per_level
    )


def test_points_never_exceed_creation_points(game_in_creation):
    for _ in range(CREATION_POINTS + 5):
        game_in_creation.handle_action(AllocatePoints(Stat.LUCK, +1))
    assert sum(game_in_creation.creation.allocated_points.values()) == CREATION_POINTS
