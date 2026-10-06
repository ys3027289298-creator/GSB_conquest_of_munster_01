"""Fixed-seed tests for random map generation and spawn results (bug #1)."""
import random

from tests.helpers import ENEMY_LETTERS, QuietTestCase, all_enemy_coords, make_game

TERRAIN_LETTERS = {"/", "=", "^", "~", "#"}
SEEDS = [0, 1, 2, 3, 7, 17, 42, 99, 123, 1234]


class MapGenerationTest(QuietTestCase):

    def test_fixed_seed_reproduces_exact_world(self):
        for seed in [0, 1, 42, 1234]:
            first = make_game(seed)
            second = make_game(seed)
            self.assertEqual(first.now_map.map, second.now_map.map)
            self.assertEqual(
                [list(g) for g in first.enemies_spawn.enemies],
                [list(g) for g in second.enemies_spawn.enemies])
            self.assertEqual(
                [[i.name for i in tile] for tile in first.items_map],
                [[i.name for i in tile] for tile in second.items_map])
            self.assertEqual(
                [npc.x for npc in first.to_index_NPC],
                [npc.x for npc in second.to_index_NPC])
            self.assertEqual(first.x, second.x)

    def test_fixed_seed_known_layout(self):
        # Pin one concrete generated world so accidental changes are visible.
        game = make_game(7)
        self.assertEqual(game.now_map.river_location, 5)
        self.assertEqual(game.x, 25)
        self.assertEqual(len(all_enemy_coords(game)), 41)

    def test_no_duplicate_enemy_spawn_points(self):
        for seed in SEEDS:
            game = make_game(seed)
            coords = all_enemy_coords(game)
            # every enemy has its own unique spawn point
            self.assertEqual(len(coords), len(set(coords)),
                             msg=f"seed {seed}: duplicate enemy spawns {coords}")
            self.assertEqual(len(coords), 41)

    def test_enemies_never_spawn_on_terrain_or_player_safe_tiles(self):
        for seed in SEEDS:
            game = make_game(seed)
            coords = set(all_enemy_coords(game))
            for coord in coords:
                self.assertNotIn(game.now_map.map[coord], TERRAIN_LETTERS,
                                 msg=f"seed {seed}: enemy on terrain at {coord}")
            occupied = set()
            for item_type in game.items_spawn.misc:
                occupied |= set(item_type)
            self.assertFalse(coords & occupied,
                             msg=f"seed {seed}: enemy spawned on an occupied tile")
            safe_tiles = {game.x + 1, game.x - 1, 15, 18}
            self.assertFalse(coords & safe_tiles,
                             msg=f"seed {seed}: enemy spawned on a first-move tile")

    def test_enemy_map_matches_spawn_data(self):
        for seed in SEEDS:
            game = make_game(seed)
            coords = set(all_enemy_coords(game))
            for tile in range(100):
                listed = tile in coords
                live = game.enemies_map[tile] != "a"
                self.assertEqual(listed, live,
                                 msg=f"seed {seed}: tile {tile} listed={listed} live={live}")
                glyph = game.now_map.map[tile]
                if glyph in ENEMY_LETTERS:
                    self.assertTrue(live,
                                    msg=f"seed {seed}: enemy glyph without enemy at {tile}")

    def test_giant_always_spawned(self):
        for seed in SEEDS:
            game = make_game(seed)
            giant_coords = game.enemies_spawn.enemies[3]
            self.assertEqual(len(giant_coords), 1)
            self.assertEqual(game.enemies_map[giant_coords[0]].name, "Giant")
