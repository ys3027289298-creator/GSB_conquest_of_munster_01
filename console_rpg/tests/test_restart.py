"""Starting a new game must reset every piece of global/run state."""
import random
import unittest

from tests.helpers import make_game_main, restart_game, state_snapshot, quiet

from game.data.characters.Enemy import Enemy
from game.data.characters.equipment.Items import Item


class TestGlobalStateReset(unittest.TestCase):
    SEED = 42

    def test_restart_returns_identical_fresh_state(self):
        game_main = make_game_main(self.SEED)
        game = game_main.game_now

        # ---- play hard: mutate every kind of state a run can mutate ----
        game.player.hp = 1
        game.player.strength = 999
        game.player.agility = 999
        game.player.Eq1.gold = 0
        game.player.Eq1.add_element("Axe")
        quiet(game.choose_direction, game.x, "d")
        # kill an enemy directly
        first_enemy = next(t for group in game.enemies_spawn.enemies
                           for t in group)
        game.enemies_map[first_enemy] = "a"
        for group in game.enemies_spawn.enemies:
            if first_enemy in group:
                group.remove(first_enemy)
        game.items_map[10].append(Item("Apple"))
        game.items_map[11] = []
        game_main.meet_mals["Guard"] = [2, 1]
        game_main.meet_mals["Monk"] = [2, 1]
        game_main.meet_mals["Alchemist"] = [2, 1]
        game.alchemist.quest = 1
        game.guard.quest = 1
        game_main.dead = 1
        game_main.save = 1
        game_main.load = 1
        game_main.end = 1
        mutated = state_snapshot(game_main)

        # sanity check: the mutations really happened
        self.assertEqual(mutated["flags"][3], 1)
        self.assertEqual(mutated["player"][0], 999)
        self.assertIn("Axe", mutated["player_eq"][0])

        # ---- restart with the same seed ----
        restart_game(game_main, self.SEED)
        restarted = state_snapshot(game_main)

        # ---- an independently started game with the same seed ----
        independent = make_game_main(self.SEED)
        fresh = state_snapshot(independent)

        self.assertEqual(restarted, fresh)

    def test_restart_resets_run_flags_and_quest_tracker(self):
        game_main = make_game_main(self.SEED)
        game_main.dead = 1
        game_main.save = 1
        game_main.load = 1
        game_main.end = 1
        game_main.meet_mals = {"Alchemist": [3, 1],
                               "Guard": [3, 1],
                               "Monk": [3, 1]}
        restart_game(game_main, self.SEED)
        self.assertEqual((game_main.save, game_main.load, game_main.end,
                          game_main.dead), (0, 0, 0, 0))
        self.assertEqual(game_main.meet_mals,
                         {"Alchemist": [0, 0], "Guard": [0, 0],
                          "Monk": [0, 0]})
        self.assertEqual(game_main.x, game_main.game_now.x)

    def test_restart_drops_old_world_objects(self):
        game_main = make_game_main(self.SEED)
        old_game = game_main.game_now
        old_player = old_game.player
        restart_game(game_main, self.SEED)
        self.assertIsNot(game_main.game_now, old_game)
        self.assertIsNot(game_main.game_now.player, old_player)
        self.assertIsNot(game_main.game_now.now_map, old_game.now_map)
        self.assertIsNot(game_main.game_now.enemies_map, old_game.enemies_map)
        self.assertIsNot(game_main.game_now.enemies_spawn,
                         old_game.enemies_spawn)


if __name__ == "__main__":
    unittest.main()
