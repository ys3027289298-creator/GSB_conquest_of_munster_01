"""Shared helpers for the console_rpg test suite.

Games are created with a fixed random seed so that map generation and
all spawn results are deterministic and can be asserted exactly.
"""
import builtins
import contextlib
import io
import itertools
import random
import unittest
import unittest.mock

import game.Game_Engine as GE
from game.data.Spawn_move_engine import Game
from game.Game_Engine import GameMain

ENEMY_LETTERS = set("bsrwdch")


def make_game(seed, race="1"):
    """Create a Game with a fixed seed and a scripted race choice."""
    random.seed(seed)
    with unittest.mock.patch.object(builtins, "input", return_value=race):
        with contextlib.redirect_stdout(io.StringIO()):
            return Game()


def make_game_main(game):
    """Build a GameMain shell around a Game without the interactive init."""
    game_main = GameMain.__new__(GameMain)
    game_main.game_now = game
    game_main.meet_mals = {"Alchemist": [0, 0], "Guard": [0, 0], "Monk": [0, 0]}
    game_main.save = 0
    game_main.load = 0
    game_main.end = 0
    game_main.dead = 0
    game_main.x = game.x
    return game_main


@contextlib.contextmanager
def fast_battle_clock():
    """Patch Game_Engine time/sleep so battles resolve instantly."""
    # 0.5s steps are exactly representable in binary floating point, so the
    # battle's int(Decimal(diff) * 10) check takes every multiple of 10 and
    # the player's hit (attack speed 10) always lands on the first round.
    clock = itertools.count(0, 0.5)
    with unittest.mock.patch.object(GE, "time", lambda: next(clock)), \
            unittest.mock.patch.object(GE, "sleep", lambda *a, **k: None):
        yield


@contextlib.contextmanager
def no_dialogue_delay():
    """Patch Game_Engine.sleep so NPC dialogues print instantly."""
    with unittest.mock.patch.object(GE, "sleep", lambda *a, **k: None):
        yield


def world_snapshot(game):
    """Capture every piece of world state that defines a game session."""
    return {
        "map": list(game.now_map.map),
        "player_x": game.x,
        "enemy_spawns": [list(group) for group in game.enemies_spawn.enemies],
        "enemies_map": [e.name if e != "a" else "a" for e in game.enemies_map],
        "items_on_ground": [[item.name for item in tile] for tile in game.items_map],
        "npc_positions": [npc.x for npc in game.to_index_NPC],
        "player_stats": (game.player.hp, game.player.hp_max, game.player.strength,
                         game.player.agility, game.player.capacity),
        "player_eq": game.player.Eq1.items_names(),
        "player_gold": game.player.Eq1.gold,
    }


def all_enemy_coords(game):
    return [coord for group in game.enemies_spawn.enemies for coord in group]


def place_player(game, tile):
    """Teleport the player icon to a tile, keeping map bookkeeping consistent."""
    game.now_map.map[game.x] = "O"
    game.now_map.map[tile] = "x"
    game.x = tile
    game.if_icon_not_to_disappear = "O"


class QuietTestCase(unittest.TestCase):
    """Suppress the game's stdout chatter inside each test."""

    def setUp(self):
        self._redirect = contextlib.redirect_stdout(io.StringIO())
        self._redirect.__enter__()
        self.addCleanup(self._redirect.__exit__, None, None, None)
