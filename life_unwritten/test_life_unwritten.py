# -*- coding: utf-8 -*-
"""Fixed-sequence tests for the single-file game life_unwritten.py.

Run with either:
    python3 life_unwritten/test_life_unwritten.py
    python3 -m unittest life_unwritten.test_life_unwritten
"""
import builtins
import io
import os
import random
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import life_unwritten  # noqa: E402
from life_unwritten import LifeUnwritten  # noqa: E402

# Opening flow: player name + "Press Enter" on the intro screen.
OPEN = ["Tester", ""]

INITIAL_BONDS = {"Maya": 60, "David": 40, "Sarah": 30, "Alex": 20}


def interact(char_index, option):
    """Reach out -> character (1-4) -> response option (1-3) -> confirm."""
    return ["1", str(char_index), str(option), ""]


def reflect(response):
    """Reflect menu (2) -> pick response (1-3) -> confirm."""
    return ["2", str(response), ""]


def end_day():
    """End the day; the confirm input also serves as an ending's finish key."""
    return ["5", ""]


def run_game(inputs, game=None, seed=42):
    """Drive one full game with a fixed input sequence.

    Returns (game, output_text). The same (inputs, seed) must always produce
    the same outcome.
    """
    random.seed(seed)
    game = game if game is not None else LifeUnwritten()
    stream = iter(inputs)

    def fake_input(prompt=""):
        try:
            return next(stream)
        except StopIteration:
            raise EOFError("scripted input exhausted")

    output = io.StringIO()
    saved_input, saved_sleep = builtins.input, life_unwritten.time.sleep
    builtins.input = fake_input
    life_unwritten.time.sleep = lambda *a, **k: None
    try:
        with redirect_stdout(output):
            game.start_game()
    finally:
        builtins.input = saved_input
        life_unwritten.time.sleep = saved_sleep
    return game, output.getvalue()


def bonds(game):
    return {n: c.bond_level for n, c in game.state.characters.items()}


class EndingReachabilityTests(unittest.TestCase):
    """Every ending must be reachable through a fixed choice sequence."""

    def test_good_ending_reachable(self):
        # Three days of best possible responses, one contact per character
        # per day: Day 3 ends with avg bond 87.25 / mood 100.
        best_day = (
            interact(1, 1) + interact(2, 1) + interact(3, 1) + interact(4, 2)
            + end_day()
        )
        game, out = run_game(OPEN + best_day * 3)
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.ending_type, "good")
        self.assertIn("A Life Rewritten", out)

    def test_bad_ending_reachable(self):
        # Worst play: each day only David's dismissive option (bond -5,
        # mood -2). From avg 37.5/mood 50 it reaches avg 30.0/mood 38 on
        # Day 6, which satisfies the (now achievable) bad-ending threshold.
        bad_day = interact(2, 3) + end_day()
        game, out = run_game(OPEN + bad_day * 6)
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.ending_type, "bad")
        self.assertIn("The Weight of Silence", out)

    def test_neutral_ending_reachable(self):
        # Do nothing for all 7 days: the time limit forces the neutral ending.
        game, out = run_game(OPEN + end_day() * 7)
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.day, 7)
        self.assertEqual(game.state.ending_type, "neutral")
        self.assertIn("A Journey Continues", out)

    def test_quit_path_reachable(self):
        game, out = run_game(OPEN + ["6"])
        self.assertTrue(game.state.game_over)
        self.assertEqual(game.state.ending_type, "")
        self.assertIn("Thanks for playing Life Unwritten", out)


class MenuBranchTests(unittest.TestCase):
    """Every main-menu branch must remain reachable."""

    def test_every_branch_reachable_in_one_sequence(self):
        sequence = (
            OPEN
            + ["3", ""]            # review choices
            + ["4", ""]            # relationship status
            + reflect(2)           # reflection
            + interact(3, 1)       # reach out to Sarah, option 1
            + ["6"]                # quit
        )
        game, out = run_game(sequence)
        self.assertIn("Your Journey So Far", out)
        self.assertIn("Relationship Status Report", out)
        self.assertIn("Time for reflection", out)
        self.assertEqual(bonds(game)["Sarah"], 48)  # 30 + 18
        self.assertEqual(len(game.state.choices_made), 2)
        self.assertTrue(game.state.game_over)

    def test_reflection_limited_to_twice_per_day(self):
        sequence = OPEN + reflect(1) + reflect(3) + ["2", ""] + ["6"]
        game, out = run_game(sequence)
        reflections = [c for c in game.state.choices_made
                       if c["choice"].startswith("Reflected on:")]
        self.assertEqual(len(reflections), 2)
        self.assertIn("You've spent enough time reflecting today", out)


class InputHandlingTests(unittest.TestCase):
    def test_invalid_inputs_never_leave_branch_or_crash(self):
        # Garbage / out-of-range entries at the main menu, the character menu
        # and the response menu must re-prompt instead of looping back or
        # raising.
        sequence = OPEN + [
            "abc", "7", "-1",      # invalid at main menu
            "1",                    # -> character menu
            "xyz", "9", "0",       # invalid inside character menu
            "1",                    # -> Maya
            "abc", "1",             # invalid then valid response
            "",                     # confirm outcome
            "6",                    # quit
        ]
        game, out = run_game(sequence)
        self.assertTrue(game.state.game_over)
        self.assertEqual(len(game.state.choices_made), 1)  # Maya interaction
        self.assertEqual(bonds(game)["Maya"], 75)          # 60 + 15, once
        self.assertGreaterEqual(out.count("Please enter a valid number"), 2)

    def test_input_stream_exhaustion_ends_safely(self):
        for inputs in ([], OPEN + ["1", "1"]):
            with self.subTest(inputs=inputs):
                game, out = run_game(inputs)
                self.assertTrue(game.state.game_over)
                self.assertNotIn("Traceback", out)


class EventRepeatTests(unittest.TestCase):
    def test_same_character_cannot_be_contacted_twice_same_day(self):
        sequence = (
            OPEN
            + interact(1, 1)       # Maya, option 1
            + ["1", "1", ""]       # second attempt blocked
            + ["6"]
        )
        game, out = run_game(sequence)
        self.assertEqual(bonds(game)["Maya"], 75)  # not 90
        self.assertEqual(
            sum(1 for c in game.state.choices_made if "Maya" in c["choice"]),
            1,
        )
        self.assertIn("already reached out to Maya today", out)

    def test_contact_allowed_again_after_new_day(self):
        sequence = (
            OPEN
            + interact(1, 1)       # Day 1: 60 -> 75
            + end_day()
            + interact(1, 1)       # Day 2: 75 -> 90
            + ["1", "1", ""]       # blocked again on Day 2
            + ["6"]
        )
        game, out = run_game(sequence)
        self.assertEqual(bonds(game)["Maya"], 90)
        self.assertEqual(game.state.day, 2)


class StatBoundsTests(unittest.TestCase):
    def test_stats_stay_in_range_across_random_playthroughs(self):
        rng = random.Random(1234)
        for _ in range(25):
            inputs = OPEN[:]
            for _ in range(7):
                chars = [1, 2, 3, 4]
                rng.shuffle(chars)
                for c in chars:
                    if rng.random() < 0.5:
                        inputs += interact(c, rng.randint(1, 3))
                for _ in range(rng.randint(0, 2)):
                    inputs += reflect(rng.randint(1, 3))
                inputs += end_day()
            game, _ = run_game(inputs, seed=rng.randrange(10_000))
            self.assertTrue(game.state.game_over)
            self.assertIn(game.state.ending_type,
                          ("good", "bad", "neutral"))
            self.assertTrue(0 <= game.state.mood <= 100)
            for name, value in bonds(game).items():
                self.assertTrue(0 <= value <= 100, f"{name} bond={value}")
            for choice in game.state.choices_made:
                self.assertTrue(0 <= choice["mood_at_time"] <= 100)


class DeterminismTests(unittest.TestCase):
    def test_same_input_sequence_gives_same_ending_and_output(self):
        best_day = (
            interact(1, 1) + interact(2, 1) + interact(3, 1) + interact(4, 2)
            + end_day()
        )
        sequence = OPEN + best_day * 3
        game1, out1 = run_game(sequence, seed=2024)
        game2, out2 = run_game(sequence, seed=2024)
        self.assertEqual(out1, out2)
        self.assertEqual(game1.state.ending_type, game2.state.ending_type)
        self.assertEqual(game1.state.mood, game2.state.mood)
        self.assertEqual(bonds(game1), bonds(game2))
        self.assertEqual(game1.state.choices_made, game2.state.choices_made)

    def test_different_seed_still_ends_at_same_ending(self):
        bad_day = interact(2, 3) + end_day()
        sequence = OPEN + bad_day * 6
        endings = {run_game(sequence, seed=s)[0].state.ending_type
                   for s in (1, 7, 99)}
        self.assertEqual(endings, {"bad"})


class ReplayTests(unittest.TestCase):
    def test_second_playthrough_starts_from_clean_state(self):
        best_day = (
            interact(1, 1) + interact(2, 1) + interact(3, 1) + interact(4, 2)
            + end_day()
        )
        game, _ = run_game(OPEN + best_day * 3)
        self.assertEqual(game.state.ending_type, "good")
        self.assertNotEqual(game.state.day, 1)

        # Replay on the SAME instance, then quit immediately.
        game, _ = run_game(OPEN + ["6"], game=game)
        self.assertEqual(game.state.day, 1)
        self.assertEqual(game.state.mood, 50)
        self.assertEqual(game.state.choices_made, [])
        self.assertEqual(game.state.reflection_count, 0)
        self.assertEqual(game.state.interactions_today, set())
        self.assertEqual(game.state.ending_type, "")
        self.assertTrue(game.state.game_over)
        self.assertEqual(bonds(game), INITIAL_BONDS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
