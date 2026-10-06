"""Shared helpers for the console_rpg test suite.

Every game object is created under a fixed ``random`` seed so that map
layout, enemy/NPC/item spawns and battle damage rolls are deterministic.
"""
import builtins
import contextlib
import io
import random
import unittest.mock

import tests  # noqa: F401  (ensures the repo root is on sys.path)

from game.data.Spawn_move_engine import Game
from game.Game_Engine import GameMain


def make_game(seed, race="1"):
    """Create a Game (world + player) with a fixed seed, no real input/output."""
    random.seed(seed)
    with unittest.mock.patch.object(builtins, "input", lambda *a, **k: race):
        with contextlib.redirect_stdout(io.StringIO()):
            return Game()


def make_game_main(seed, race="1"):
    """Create a GameMain in a fresh run state without the interactive __init__."""
    game_main = GameMain.__new__(GameMain)
    random.seed(seed)
    with unittest.mock.patch.object(builtins, "input", lambda *a, **k: race):
        with contextlib.redirect_stdout(io.StringIO()):
            if hasattr(game_main, "start_new_game"):
                game_main.start_new_game()
            else:
                # legacy path: the unfixed engine has no reset API
                game_main.save = 0
                game_main.load = 0
                game_main.end = 0
                game_main.dead = 0
                game_main.x = 0
                game_main.meet_mals = {"Alchemist": [0, 0], "Guard": [0, 0],
                                       "Monk": [0, 0]}
                game_main.game_now = Game()
                game_main.x = game_main.game_now.x
    return game_main


def restart_game(game_main, seed, race="1"):
    """Restart an existing GameMain with a fixed seed (new run, same object)."""
    random.seed(seed)
    with unittest.mock.patch.object(builtins, "input", lambda *a, **k: race):
        with contextlib.redirect_stdout(io.StringIO()):
            return game_main.start_new_game()


def quiet(callable_, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return callable_(*args, **kwargs)


def state_snapshot(game_main):
    """A comparable snapshot of the complete global/run state of a game."""
    game = game_main.game_now
    return {
        "flags": (game_main.save, game_main.load, game_main.end,
                  game_main.dead, game_main.x),
        "meet_mals": {k: list(v) for k, v in game_main.meet_mals.items()},
        "map": list(game.now_map.map),
        "camp_gate": game.now_map.camp_gate,
        "player_x": game.x,
        "player": (game.player.strength, game.player.agility,
                   game.player.hp, game.player.hp_max),
        "player_eq": ([item.name for item in game.player.Eq1.elements],
                      game.player.Eq1.gold, game.player.Eq1.capacity),
        "enemies_spawn": [list(group) for group in game.enemies_spawn.enemies],
        "enemies_map": [enemy.name if enemy != "a" else "a"
                        for enemy in game.enemies_map],
        "npc_positions": [npc.x for npc in game.to_index_NPC],
        "npc_quests": [npc.quest for npc in game.to_index_NPC],
        "items_map": [[item.name for item in tile] for tile in game.items_map],
        "icon_memory": game.if_icon_not_to_disappear,
    }
