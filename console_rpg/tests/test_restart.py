"""Restarting a game must reset all state: a brand-new Game created after
an old session was mutated has to be identical to a pristine first session
(no leaked module-level or shared mutable state)."""
import random

from tests.helpers import (QuietTestCase, all_enemy_coords, fast_battle_clock,
                           make_game, make_game_main, no_dialogue_delay,
                           place_player, world_snapshot)

SEEDS = [0, 1, 42, 1234]


class RestartResetTest(QuietTestCase):

    def mutate_session(self, game):
        """Play a bit: fight, walk, loot, talk, spend - dirty the session."""
        game_main = make_game_main(game)
        game.player.strength = 100000
        # slay an enemy for real
        enemy_tile = game.enemies_spawn.enemies[2][0]
        for delta, direction in {-10: "w", 10: "s", -1: "a", 1: "d"}.items():
            neighbour = enemy_tile - delta
            if 0 <= neighbour <= 99 and game.check_possibility_to_move(neighbour, enemy_tile):
                place_player(game, neighbour)
                game.choose_direction(neighbour, direction)
                break
        random.seed(1)
        with fast_battle_clock():
            game_main.battle(enemy_tile)
        # walk around
        for direction in ["s", "d", "w", "a"]:
            game.choose_direction(game.x, direction)
        # loot a tile that has items
        for tile in range(100):
            if game.items_map[tile]:
                game_main.collect_items(tile)
                break
        # talk to an NPC (advances quest state)
        with no_dialogue_delay():
            game_main.talk(game.alchemist.x)
        # change player state directly
        game.player.hp = 1
        game.player.Eq1.gold = 0
        return game_main

    def test_restart_resets_all_global_state(self):
        for seed in SEEDS:
            pristine = make_game(seed)
            pristine_snapshot = world_snapshot(pristine)

            dirty = make_game(seed)
            self.mutate_session(dirty)
            self.assertNotEqual(world_snapshot(dirty), pristine_snapshot,
                                msg="mutation had no effect, test is useless")

            restarted = make_game(seed)
            self.assertEqual(world_snapshot(restarted), pristine_snapshot,
                             msg=f"seed {seed}: restart did not fully reset the game")

    def test_fresh_game_invariants_after_mutation(self):
        make_game(0)  # first session
        dirty = make_game(0)
        self.mutate_session(dirty)
        fresh = make_game(0)
        # every enemy alive again
        self.assertEqual(len(all_enemy_coords(fresh)), 41)
        # player fully restored
        self.assertEqual(fresh.player.hp, fresh.player.hp_max)
        self.assertEqual(fresh.player.Eq1.gold, 100)
        self.assertEqual(fresh.player.Eq1.items_names(),
                         ["Sword", "Potato", "Bottle of Water", "HP Potion", "Strength Potion"])
        # exactly one player icon at the spawn point
        self.assertEqual(fresh.now_map.map.count("x"), 1)
        self.assertEqual(fresh.now_map.map[fresh.x], "x")
        # no quest progress leaked into the new session
        self.assertEqual(fresh.alchemist.quest, 0)
        self.assertEqual(fresh.guard.quest, 0)
        self.assertEqual(fresh.monk.quest, 0)
