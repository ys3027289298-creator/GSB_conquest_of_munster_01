"""Bug 6: out-of-bounds player movement must be rejected, never crash."""
import unittest

from tests.helpers import make_game, quiet


class TestBounds(unittest.TestCase):
    def test_all_moves_stay_inside_map(self):
        game = make_game(3)
        for x in range(100):
            for direction in ("w", "s", "a", "d"):
                new_x = quiet(game.choose_direction, x, direction)
                self.assertGreaterEqual(new_x, 0)
                self.assertLessEqual(new_x, 99)

    def test_direct_bounds_check(self):
        game = make_game(3)
        for x in range(100):
            for check in range(-130, 140):
                if not (0 <= check <= 99):
                    self.assertFalse(
                        game.check_possibility_to_move(x, check),
                        f"accepted out-of-bounds target {check} from {x}")

    def test_top_left_corner_cannot_wrap_to_bottom(self):
        game = make_game(1)
        game.x = 0
        game.now_map.map[0] = "x"
        game.now_map.map[90] = "O"  # free tile that -10 would alias to
        new_x = quiet(game.choose_direction, 0, "w")
        self.assertEqual(new_x, 0)
        # negative index must not have corrupted the bottom row
        self.assertNotEqual(game.now_map.map[90], "x")

    def test_bottom_row_and_right_column_blocked(self):
        game = make_game(1)
        for x in range(90, 100):
            self.assertEqual(quiet(game.choose_direction, x, "s"), x)
        for x in (9, 19, 29, 39, 49, 59, 69, 79, 89, 99):
            self.assertEqual(quiet(game.choose_direction, x, "d"), x)

    def test_negative_position_cannot_alias_an_enemy(self):
        game = make_game(1)
        from game.data.characters.Enemy import Enemy
        # an enemy at tile 90 used to be reachable as enemies_map[-10]
        game.enemies_map[90] = Enemy("Wolf")
        game.enemies_spawn.enemies[4].append(90)
        self.assertTrue(game.check_if_able_to_fight(90))
        # the player can never actually stand at -10, so no battle is possible
        self.assertEqual(quiet(game.choose_direction, 0, "w"), 0)


if __name__ == "__main__":
    unittest.main()
