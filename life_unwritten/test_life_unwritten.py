"""Tests for life_unwritten.py.

Drives the game with fixed, scripted input sequences (input()/time.sleep patched)
and verifies:
  - each menu branch and every ending path is reachable
  - invalid numeric input is re-prompted in place (no exception, no desync)
  - mood/bond attributes stay within 0-100
  - the same character event cannot be re-triggered on the same day
  - replaying on the same instance leaves no residual state
  - the same input sequence (with the same seed) always yields the same ending
"""

import builtins
import importlib.util
import io
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("life_unwritten.py")
spec = importlib.util.spec_from_file_location("life_unwritten", MODULE_PATH)
lu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lu)

SEED = 7

GOOD_ENDING = "ENDING: A Life Rewritten"
BAD_ENDING = "ENDING: The Weight of Silence"
NEUTRAL_ENDING = "ENDING: A Journey Continues"


def drive(game, inputs):
    """Run start_game() on an instance with scripted input; return (output, error)."""
    queue = iter(inputs)
    old_input, old_sleep = builtins.input, time.sleep

    def fake_input(prompt=""):
        try:
            return next(queue)
        except StopIteration:
            raise EOFError("scripted input exhausted")

    builtins.input = fake_input
    time.sleep = lambda *_args: None
    buf = io.StringIO()
    error = None
    try:
        with redirect_stdout(buf):
            game.start_game()
    except EOFError:
        error = "EOF"
    finally:
        builtins.input, time.sleep = old_input, old_sleep
    return buf.getvalue(), error


def run_game(inputs, seed=SEED):
    """Fresh seeded game driven by a fixed input sequence."""
    game = lu.LifeUnwritten(seed=seed)
    output, error = drive(game, inputs)
    return game, output, error


def snapshot(game):
    state = game.state
    return (
        state.day,
        state.mood,
        tuple(sorted((name, c.bond_level) for name, c in state.characters.items())),
        tuple((c["day"], c["choice"], c["impact"], c["mood_at_time"]) for c in state.choices_made),
        state.game_over,
    )


# One day of best-bond interactions with all four characters, then end the day.
BEST_DAY = [
    "1", "1", "1", "",   # Maya  -> option 1 (+15 bond, +5 mood)
    "1", "2", "1", "",   # David -> option 1 (+20 bond, +8 mood)
    "1", "3", "1", "",   # Sarah -> option 1 (+18 bond, +6 mood)
    "1", "4", "2", "",   # Alex  -> option 2 (+15 bond, +5 mood)
    "5",                 # back to main menu
    "5", "",             # end the day / press enter (or finish on ending)
]

# One day of the only bond-negative choice, then end the day.
WORST_DAY = [
    "1", "2", "3", "",   # David -> option 3 (-5 bond, -2 mood)
    "5",                 # back to main menu
    "5", "",             # end the day / press enter (or finish on ending)
]

GOOD_PATH = ["Tester", ""] + BEST_DAY * 3
BAD_PATH = ["Tester", ""] + WORST_DAY * 6
NEUTRAL_PATH = ["Tester", ""] + ["5", ""] * 7
REFLECT_DAY = ["2", "1", "", "2", "2", "", "5", ""]  # reflect twice, end day
REFLECT_PATH = ["Tester", ""] + REFLECT_DAY * 7


class TestPathsReachable(unittest.TestCase):
    def test_good_ending_reachable(self):
        game, out, err = run_game(GOOD_PATH)
        self.assertIsNone(err)
        self.assertIn(GOOD_ENDING, out)
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.day, 3)

    def test_bad_ending_reachable(self):
        game, out, err = run_game(BAD_PATH)
        self.assertIsNone(err)
        self.assertIn(BAD_ENDING, out)
        self.assertTrue(game.state.game_over)

    def test_neutral_ending_reachable(self):
        game, out, err = run_game(NEUTRAL_PATH)
        self.assertIsNone(err)
        self.assertIn(NEUTRAL_ENDING, out)
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.day, 7)

    def test_quit_path(self):
        game, out, err = run_game(["Tester", "", "6"])
        self.assertIsNone(err)
        self.assertTrue(game.state.game_over)
        self.assertNotIn("ENDING:", out)

    def test_review_and_status_branches_reachable(self):
        game, out, err = run_game(["Tester", "", "3", "", "4", "", "6"])
        self.assertIsNone(err)
        self.assertIn("Your Journey So Far", out)
        self.assertIn("Relationship Status Report", out)
        self.assertTrue(game.state.game_over)


class TestInputValidation(unittest.TestCase):
    def test_invalid_numbers_reprompt_without_exception(self):
        inputs = [
            "Tester", "",
            "xyz", "9", "0", "-1", "2.5",  # garbage at main menu
            "1",                              # -> interaction submenu
            "abc", "", "99",                  # garbage at character menu
            "2",                              # -> David
            "nope", "4", "0",                 # garbage at response menu
            "1", "",                          # valid choice, continue
            "5",                              # back to main menu
            "6",                              # quit
        ]
        game, out, err = run_game(inputs)
        self.assertIsNone(err)
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.characters["David"].bond_level, 60)

    def test_invalid_input_does_not_desync_menus(self):
        # Regression: invalid input used to bounce to the main menu, so the next
        # input ("2") was consumed by the wrong menu and triggered reflection.
        inputs = ["Tester", "", "1", "abc", "2", "1", "", "5", "6"]
        game, out, err = run_game(inputs)
        self.assertIsNone(err)
        self.assertEqual(game.state.reflection_count, 0)
        self.assertEqual(game.state.characters["David"].bond_level, 60)
        self.assertEqual(len(game.state.choices_made), 1)
        self.assertIn("David", game.state.choices_made[0]["choice"])

    def test_invalid_reflection_choice_reprompts(self):
        game, out, err = run_game(["Tester", "", "2", "abc", "1", "", "6"])
        self.assertIsNone(err)
        self.assertEqual(game.state.reflection_count, 1)
        self.assertGreater(game.state.mood, 50)


class TestAttributeBounds(unittest.TestCase):
    def test_clamp_stat(self):
        game = lu.LifeUnwritten(seed=SEED)
        self.assertEqual(game.clamp_stat(-10), 0)
        self.assertEqual(game.clamp_stat(150), 100)
        self.assertEqual(game.clamp_stat(50), 50)

    def test_extreme_choice_outcomes_stay_in_bounds(self):
        game = lu.LifeUnwritten(seed=SEED)
        maya = game.state.characters["Maya"]
        maya.bond_level = 5
        game.state.mood = 3
        with redirect_stdout(io.StringIO()):
            old_input = builtins.input
            builtins.input = lambda prompt="": ""
            try:
                game.process_interaction_choice(maya, {"text": "t", "bond_change": -999, "mood_change": -999})
            finally:
                builtins.input = old_input
        self.assertEqual(maya.bond_level, 0)
        self.assertEqual(game.state.mood, 0)

    def test_full_playthrough_attributes_in_bounds(self):
        for path in (GOOD_PATH, BAD_PATH, NEUTRAL_PATH, REFLECT_PATH):
            game, _out, err = run_game(path)
            self.assertIsNone(err)
            self.assertGreaterEqual(game.state.mood, 0)
            self.assertLessEqual(game.state.mood, 100)
            for char in game.state.characters.values():
                self.assertGreaterEqual(char.bond_level, 0)
                self.assertLessEqual(char.bond_level, 100)


class TestEventRepeat(unittest.TestCase):
    def test_same_character_not_repeatable_same_day(self):
        inputs = [
            "Tester", "",
            "1", "1", "1", "",   # talk to Maya (option 1)
            "1",                  # try Maya again -> blocked, re-prompt
            "5",                  # back
            "5", "",              # end day -> day 2
            "1", "1", "1", "",   # Maya available again on day 2
            "5",                  # back
            "6",                  # quit
        ]
        game, out, err = run_game(inputs)
        self.assertIsNone(err)
        self.assertIn("already talked to Maya today", out)
        self.assertEqual(game.state.day, 2)
        self.assertEqual(game.state.characters["Maya"].bond_level, 60 + 15 + 15)
        maya_talks = [c for c in game.state.choices_made if "Maya" in c["choice"]]
        self.assertEqual(len(maya_talks), 2)


class TestReplayReset(unittest.TestCase):
    def test_replay_leaves_no_residual_state(self):
        game = lu.LifeUnwritten(seed=SEED)
        out1, err1 = drive(game, ["First", "", "1", "1", "1", "", "5", "6"])
        self.assertIsNone(err1)
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.characters["Maya"].bond_level, 75)

        out2, err2 = drive(game, ["Second", "", "6"])
        self.assertIsNone(err2)
        self.assertIn("Second", out2)
        self.assertEqual(game.state.player_name, "Second")
        self.assertEqual(game.state.day, 1)
        self.assertEqual(game.state.mood, 50)
        self.assertEqual(game.state.choices_made, [])
        self.assertEqual(game.state.reflection_count, 0)
        self.assertEqual(game.state.interacted_today, set())
        self.assertEqual(game.state.characters["Maya"].bond_level, 60)
        self.assertTrue(game.state.game_over)  # quit during replay actually worked


class TestDeterminism(unittest.TestCase):
    def test_same_input_sequence_same_ending(self):
        for path, ending in ((GOOD_PATH, GOOD_ENDING), (BAD_PATH, BAD_ENDING),
                             (NEUTRAL_PATH, NEUTRAL_ENDING), (REFLECT_PATH, NEUTRAL_ENDING)):
            results = [run_game(path) for _ in range(3)]
            for game, out, err in results:
                self.assertIsNone(err)
                self.assertIn(ending, out)
            snapshots = [snapshot(game) for game, _out, _err in results]
            self.assertTrue(all(s == snapshots[0] for s in snapshots),
                            f"same input sequence produced divergent states: {snapshots}")
            outputs = [out for _game, out, _err in results]
            self.assertTrue(all(o == outputs[0] for o in outputs),
                            "same input sequence produced divergent transcripts")

    def test_replay_same_sequence_same_result(self):
        game = lu.LifeUnwritten(seed=SEED)
        drive(game, GOOD_PATH)
        first = snapshot(game)
        drive(game, GOOD_PATH)
        second = snapshot(game)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
