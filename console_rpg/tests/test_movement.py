"""The player can never leave the 10x10 map (bug #6): out-of-bounds moves
used to wrap around to negative indexes and crash the game later."""
from tests.helpers import QuietTestCase, make_game

DELTAS = {"w": -10, "s": 10, "a": -1, "d": 1}
TERRAIN = {"/", "=", "^", "~", "#"}


class MovementBoundsTest(QuietTestCase):

    def setUp(self):
        super().setUp()
        self.game = make_game(0)

    def test_no_move_ever_leaves_the_map(self):
        game = self.game
        for tile in range(100):
            for direction, delta in DELTAS.items():
                target = tile + delta
                # clear the target (and its wrap-around alias) so terrain
                # can never mask an out-of-bounds wrap bug
                game.now_map.map[target % 100] = "O"
                game.now_map.map[game.x] = "O"
                game.now_map.map[tile] = "x"
                game.x = tile
                new_x = game.choose_direction(tile, direction)
                self.assertTrue(0 <= new_x <= 99,
                                msg=f"move {direction!r} from {tile} escaped to {new_x}")
                self.assertEqual(game.now_map.map.count("x"), 1)
                game.now_map.map[new_x] = "O"

    def test_corner_and_edge_moves_are_blocked(self):
        game = self.game
        cases = [
            (0, "w"), (0, "a"), (9, "w"), (9, "d"),
            (90, "a"), (90, "s"), (99, "s"), (99, "d"),
            (5, "w"), (95, "s"), (10, "a"), (19, "d"),
        ]
        for tile, direction in cases:
            target = tile + DELTAS[direction]
            # clear the wrap-around alias as well: with the old bug a move
            # off the top edge wrapped to the bottom row instead of stopping
            game.now_map.map[target % 100] = "O"
            game.now_map.map[game.x] = "O"
            game.now_map.map[tile] = "x"
            game.x = tile
            self.assertEqual(game.choose_direction(tile, direction), tile,
                             msg=f"move {direction!r} from {tile} should be blocked")

    def test_legal_moves_still_work(self):
        game = self.game
        for tile in [44, 11, 55, 38]:
            for direction, delta in DELTAS.items():
                target = tile + delta
                game.now_map.map[target] = "O"
                game.now_map.map[game.x] = "O"
                game.now_map.map[tile] = "x"
                game.x = tile
                self.assertEqual(game.choose_direction(tile, direction), target,
                                 msg=f"move {direction!r} from {tile} should be legal")
                game.now_map.map[target] = "O"

    def test_terrain_still_blocks_movement(self):
        game = self.game
        game.now_map.map[45] = "^"
        game.now_map.map[game.x] = "O"
        game.now_map.map[44] = "x"
        game.x = 44
        self.assertEqual(game.choose_direction(44, "d"), 44)
