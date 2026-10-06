"""Bug 2: a slain enemy must not keep acting or linger on the map."""
import unittest
import unittest.mock

import game.Game_Engine as GameEngineModule
from tests.helpers import make_game, make_game_main, quiet

from game.data.characters.Enemy import Enemy


class VirtualClock:
    """Deterministic time(): each call advances by a fixed step."""

    def __init__(self, step=0.025, max_calls=None):
        self.now = 0.0
        self.step = step
        self.calls = 0
        self.max_calls = max_calls

    def __call__(self):
        self.calls += 1
        if self.max_calls is not None and self.calls > self.max_calls:
            raise AssertionError("battle did not terminate: dead enemy kept acting")
        self.now += self.step
        return self.now


def run_battle(game_main, x, clock=None):
    clock = clock or VirtualClock()
    with unittest.mock.patch.object(GameEngineModule, "sleep", lambda *a: None):
        with unittest.mock.patch.object(GameEngineModule, "time", clock):
            return quiet(game_main.battle, x)


def place_enemy(game, tile, name="Rat"):
    game.enemies_map[tile] = Enemy(name)
    group = {"Bandit": 0, "Skeleton": 1, "Rat": 2, "Giant": 3,
             "Wolf": 4, "Dwarf": 5, "Cobra": 6, "Hyaena": 7}[name]
    if tile not in game.enemies_spawn.enemies[group]:
        game.enemies_spawn.enemies[group].append(tile)
    glyph = {"Bandit": "b", "Skeleton": "s", "Rat": "r", "Giant": "O",
             "Wolf": "w", "Dwarf": "d", "Cobra": "c", "Hyaena": "h"}[name]
    game.now_map.map[tile] = glyph


class TestDeadEnemyStaysDead(unittest.TestCase):
    def test_killed_enemy_is_fully_removed(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        place_enemy(game, 47, "Rat")
        game.player.strength = 60
        game.player.agility = 40
        run_battle(game_main, 47)
        self.assertEqual(game.enemies_map[47], "a")
        for group in game.enemies_spawn.enemies:
            self.assertNotIn(47, group)
        self.assertFalse(game.check_if_able_to_fight(47))
        self.assertEqual(game_main.dead, 0)

    def test_corpse_glyph_does_not_linger_on_map(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        place_enemy(game, 47, "Rat")
        game.player.strength = 60
        game.player.agility = 40
        # player walks onto the enemy tile (icon remembered), kills it, walks off
        game.now_map.map[game.x] = "O"
        game.x = 46
        game.now_map.map[46] = "x"
        quiet(game.choose_direction, 46, "d")
        run_battle(game_main, 47)
        new_x = quiet(game.choose_direction, 47, "d")
        self.assertNotEqual(new_x, 47)
        self.assertEqual(game.now_map.map[47], "O")

    def test_enemy_cannot_strike_after_death_same_tick(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        place_enemy(game, 47, "Rat")
        # player attack interval equals the rat's (both 20 ticks):
        # the killing blow and the rat's attack land in the same iteration
        game.player.strength = 25   # 25 * 10 = 250 dmg >= rat hp 200
        game.player.agility = 10    # 10 * 5 = 50 -> same interval as the rat
        run_battle(game_main, 47)
        self.assertEqual(game.enemies_map[47], "a")
        self.assertEqual(game.player.hp, 400)
        self.assertEqual(game_main.dead, 0)

    def test_skipped_attack_tick_cannot_softlock_battle(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        place_enemy(game, 47, "Rat")
        game.player.strength = 25
        game.player.agility = 40   # player_as == 5 ticks
        # clock jumps straight past tick 5 (0 -> 10): with a strict "=="
        # comparison the player would never attack again while the enemy
        # keeps hitting; with ">=" the player strikes as soon as possible
        clock = VirtualClock(step=0.525, max_calls=500)
        run_battle(game_main, 47, clock=clock)
        self.assertEqual(game.enemies_map[47], "a")
        self.assertEqual(game_main.dead, 0)
        self.assertGreater(game.player.hp, 0)


if __name__ == "__main__":
    unittest.main()
