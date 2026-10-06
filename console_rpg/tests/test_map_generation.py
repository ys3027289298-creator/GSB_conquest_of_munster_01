"""Fixed-seed map / spawn generation tests (bug 1: duplicate spawn points)."""
import io
import random
import unittest

from tests.helpers import make_game

from game.data.random_map.Map import MapNew


class TestMapDeterminism(unittest.TestCase):
    def test_map_pinned_seed_7(self):
        random.seed(7)
        world = MapNew()
        self.assertEqual(
            "".join(world.map),
            "/////O^^^^///OOOO^^^OOOOOOOOO^OOOOO=OOOO###O==OOOO=====OOOOOO~OOOOOO##~~"
            "OOOOOO##//OOOOOO##///OOOOOOO",
        )
        self.assertEqual((world.river_location, world.mountain_location,
                          world.city_location, world.village_location),
                         (5, 0, 6, 4))
        self.assertEqual(world.sea_location, [0, 9])
        self.assertEqual(world.camp_location, 6)
        self.assertEqual(world.camp_gate, 61)

    def test_map_pinned_seed_42(self):
        random.seed(42)
        world = MapNew()
        self.assertEqual(
            "".join(world.map),
            "///OOO^^^^OOOOOOO^^^OOOOOOOOO^###OOOOOOO=====OOOOOO~OO==OOOO~~OOO=OOOO"
            "OOOOOOOO##///OOOOO##/////OOO##",
        )
        self.assertEqual((world.river_location, world.mountain_location,
                          world.city_location, world.village_location),
                         (4, 0, 7, 3))
        self.assertEqual(world.sea_location, [9, 0])
        self.assertEqual(world.camp_location, 5)
        self.assertEqual(world.camp_gate, 51)

    def test_same_seed_same_map(self):
        random.seed(123)
        first = MapNew()
        random.seed(123)
        second = MapNew()
        self.assertEqual(first.map, second.map)
        self.assertEqual((first.river_location, first.mountain_location,
                          first.city_location, first.village_location,
                          first.sea_location, first.camp_location,
                          first.camp_gate),
                         (second.river_location, second.mountain_location,
                          second.city_location, second.village_location,
                          second.sea_location, second.camp_location,
                          second.camp_gate))

    def test_terrain_invariants(self):
        for seed in range(50):
            random.seed(seed)
            world = MapNew()
            self.assertEqual(len(world.map), 100)
            for glyph in ("=", "^", "/", "~", "#"):
                self.assertIn(glyph, world.map)


class TestSpawnDeterminism(unittest.TestCase):
    def test_world_pinned_seed_42(self):
        game = make_game(42)
        self.assertEqual(game.x, 75)
        self.assertEqual(game.enemies_spawn.enemies,
                         [[16, 27, 28], [3, 12, 13],
                          [77, 87, 97, 20, 21, 22], [50],
                          [5, 24, 46, 48, 86, 10, 47],
                          [73, 35, 58, 67, 37, 95, 4],
                          [96, 33, 85, 63, 57, 49, 26],
                          [39, 68, 25, 14, 62, 23, 66]])
        self.assertEqual(game.NPC_spawn.NPC,
                         [88, 79, 89, 78, 98, 99, 32, 31, 30])

    def test_same_seed_same_world(self):
        first = make_game(2024)
        second = make_game(2024)
        self.assertEqual(first.now_map.map, second.now_map.map)
        self.assertEqual(first.enemies_spawn.enemies, second.enemies_spawn.enemies)
        self.assertEqual(first.NPC_spawn.NPC, second.NPC_spawn.NPC)
        self.assertEqual([[item.name for item in tile]
                          for tile in first.items_map],
                         [[item.name for item in tile]
                          for tile in second.items_map])


class TestNoDuplicateSpawns(unittest.TestCase):
    def test_every_enemy_owns_unique_free_tile(self):
        for seed in range(50):
            game = make_game(seed)
            all_enemy_tiles = [tile for group in game.enemies_spawn.enemies
                               for tile in group]
            # no tile hosts two enemies
            self.assertEqual(len(all_enemy_tiles), len(set(all_enemy_tiles)),
                             f"duplicate enemy spawn with seed {seed}")
            # the player's own tile cannot host an enemy
            self.assertNotIn(game.x, all_enemy_tiles)
            # no enemy may spawn on the protected first-move zone
            first_move = {game.x + 1, game.x - 1, 15, 18}
            rest_tiles = [tile for group in game.enemies_spawn.enemies[4:]
                          for tile in group]
            self.assertEqual(set(rest_tiles) & first_move, set(),
                             f"enemy spawned in start zone with seed {seed}")
            # enemy glyphs, enemies_map objects and spawn lists must agree
            glyphs = {"b", "s", "r", "w", "d", "c", "h"}
            for tile in range(100):
                if game.now_map.map[tile] in glyphs:
                    self.assertTrue(game.check_if_able_to_fight(tile),
                                    f"glyph without Enemy object at {tile}")
            # the giant (glyph "O") must exist as an object on its spawn tile
            giant_tile = game.enemies_spawn.enemies[3][0]
            self.assertEqual(game.enemies_map[giant_tile].name, "Giant")

    def test_scattered_items_use_distinct_tiles(self):
        for seed in range(50):
            game = make_game(seed)
            item_tiles = [tile for tile, items in enumerate(game.items_map)
                          if items]
            total_items = sum(len(items) for items in game.items_map)
            # 5 reeds + 40 scattered items; scattered ones never stack
            self.assertEqual(total_items, 45)
            self.assertGreaterEqual(len(item_tiles), 40,
                                    f"items stacked through duplicate spawn seed {seed}")


if __name__ == "__main__":
    unittest.main()
