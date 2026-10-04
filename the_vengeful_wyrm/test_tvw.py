"""
Fixed-seed regression tests for the_vengeful_wyrm.

Run from this directory:
    python3 -m unittest test_tvw -v

Covers:
- dice determinism and ranges under a fixed seed
- character state invariants (hit points never leave [0, max])
- health bar rendering without negative values
- failure paths (mission decline, failed riddle, failed swim, lost fight)
  never advancing the mission: the game returns False and no Happy End
"""

import builtins
import contextlib
import io
import random
import time
import unittest

import tvw_test_support as support

support.install_stubs()

import tvw_dices
import tvw_fight
import tvw_healthbar
import tvw_mission
import tvw_path
import tvw_game

time.sleep = lambda *a, **k: None  # keep tests fast

DWARF = {"race": "dwarf", "class": "fighter", "hit points": 15, "armor_class": 12,
         "weapon": "battle axe", "initiative bonus": 2, "attack bonus": 3,
         "damage": 2, "athletics": 1}
WYRM = {"race": "wyrm", "class": "fighter", "hit points": 20, "armor_class": 10,
        "weapon": "tale", "initiative bonus": 1, "attack bonus": 1, "damage": 2}

WIN_ROLLS = {"tvw_fight__user_D20": lambda: 20, "tvw_fight__user_D6": lambda u: 6,
             "tvw_fight__enemy_D20": lambda: 1, "tvw_fight__enemy_D6": lambda w: 1}
LOSS_ROLLS = {"tvw_fight__user_D20": lambda: 1, "tvw_fight__user_D6": lambda u: 1,
              "tvw_fight__enemy_D20": lambda: 20, "tvw_fight__enemy_D6": lambda w: 6}


def run_with_input(answers, callable_, *args, **kwargs):
    fake = support.FakeInput(answers)
    original = builtins.input
    builtins.input = fake
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = callable_(*args, **kwargs)
    finally:
        builtins.input = original
    return result, buf.getvalue(), fake


class DiceTests(unittest.TestCase):
    def test_enemy_d20_reproducible_with_fixed_seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            random.seed(2024)
            first = [tvw_dices.enemy_D20() for _ in range(20)]
            random.seed(2024)
            second = [tvw_dices.enemy_D20() for _ in range(20)]
        self.assertEqual(first, second)
        self.assertTrue(all(1 <= roll <= 20 for roll in first))

    def test_enemy_d6_reproducible_with_fixed_seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            random.seed(99)
            first = [tvw_dices.enemy_D6(WYRM) for _ in range(20)]
            random.seed(99)
            second = [tvw_dices.enemy_D6(WYRM) for _ in range(20)]
        self.assertEqual(first, second)
        self.assertTrue(all(1 <= roll <= 6 for roll in first))

    def test_user_d20_reproducible_with_fixed_seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            random.seed(7)
            builtins.input = support.FakeInput(["roll"] * 20)
            first = [tvw_dices.user_D20() for _ in range(20)]
            random.seed(7)
            builtins.input = support.FakeInput(["roll"] * 20)
            second = [tvw_dices.user_D20() for _ in range(20)]
        builtins.input = input
        self.assertEqual(first, second)
        self.assertTrue(all(1 <= roll <= 20 for roll in first))

    def test_user_d6_adds_damage_modifier(self):
        random.seed(42)
        with contextlib.redirect_stdout(io.StringIO()):
            builtins.input = support.FakeInput(["roll"])
            total = tvw_dices.user_D6(dict(DWARF))
        builtins.input = input
        self.assertIn(total - DWARF["damage"], range(1, 7))

    def test_seeded_fight_is_deterministic(self):
        outcomes = []
        for _ in range(2):
            random.seed(1234)
            builtins.input = support.FakeInput(["roll"] * 200)
            with contextlib.redirect_stdout(io.StringIO()):
                user, enemy = dict(DWARF), dict(WYRM)
                won = tvw_fight.fight(user, enemy, "Test")
            builtins.input = input
            outcomes.append((won, user["hit points"], enemy["hit points"]))
        self.assertEqual(outcomes[0], outcomes[1])


class StateTests(unittest.TestCase):
    def test_enemy_attack_clamps_user_hp_at_zero(self):
        user = {"hit points": 3, "armor_class": 10, "damage": 2}
        enemy = {"hit points": 20, "armor_class": 10, "attack bonus": 1, "damage": 2}
        with contextlib.redirect_stdout(io.StringIO()):
            tvw_fight.enemy_attack(lambda: 20, lambda w: 6, user, enemy)
        self.assertEqual(user["hit points"], 0)

    def test_user_attack_clamps_enemy_hp_at_zero(self):
        user = {"hit points": 15, "armor_class": 12, "attack bonus": 3, "damage": 2}
        enemy = {"hit points": 4, "armor_class": 10}
        with contextlib.redirect_stdout(io.StringIO()):
            tvw_fight.user_attack(lambda: 20, lambda u: 8, user, enemy)
        self.assertEqual(enemy["hit points"], 0)

    def test_healthbar_never_shows_negative(self):
        entity = {"hit points": 15}
        bar = tvw_healthbar.HealthBar(entity)
        entity["hit points"] = -5
        bar.update()
        _, output, _ = run_with_input([], bar.draw)
        self.assertIn("YOUR HEALTH: 0/15", output)
        self.assertEqual(output.count(tvw_healthbar.HealthBar.symbol_remaining), 0)
        self.assertEqual(output.count(tvw_healthbar.HealthBar.symbol_lost), 20)

    def test_healthbar_partial_damage(self):
        entity = {"hit points": 15}
        bar = tvw_healthbar.HealthBar(entity)
        entity["hit points"] = 7
        bar.update()
        _, output, _ = run_with_input([], bar.draw)
        self.assertIn("YOUR HEALTH: 7/15", output)
        self.assertEqual(output.count(tvw_healthbar.HealthBar.symbol_remaining), 9)
        self.assertEqual(output.count(tvw_healthbar.HealthBar.symbol_lost), 11)

    def test_fight_returns_false_and_clamps_on_defeat(self):
        user, enemy = dict(DWARF), dict(WYRM)
        with support.patched(**LOSS_ROLLS):
            won, output, _ = run_with_input([], tvw_fight.fight, user, enemy, "Test")
        self.assertIs(won, False)
        self.assertEqual(user["hit points"], 0)
        self.assertIn("defeated", output.lower())

    def test_fight_returns_true_and_clamps_on_victory(self):
        user, enemy = dict(DWARF), dict(WYRM)
        with support.patched(**WIN_ROLLS):
            won, output, _ = run_with_input([], tvw_fight.fight, user, enemy, "Test")
        self.assertIs(won, True)
        self.assertEqual(enemy["hit points"], 0)
        self.assertIn("Happy end", output)


class MissionTests(unittest.TestCase):
    def test_mission_accept_returns_true(self):
        with support.narrative_cwd():
            result, _, _ = run_with_input(["yes"], tvw_mission.mission, "Hero")
        self.assertIs(result, True)

    def test_mission_decline_returns_false(self):
        with support.narrative_cwd():
            result, _, _ = run_with_input(["no"], tvw_mission.mission, "Hero")
        self.assertIs(result, False)

    def test_confirmed_decline_does_not_advance(self):
        with support.narrative_cwd():
            result, _, _ = run_with_input(["yes"], tvw_mission.mission_decision, False, "Hero")
        self.assertIs(result, False)

    def test_reconsidered_decline_advances_once(self):
        with support.narrative_cwd():
            result, _, _ = run_with_input(["no"], tvw_mission.mission_decision, False, "Hero")
        self.assertIs(result, True)


class PathTests(unittest.TestCase):
    def test_riddle_correct_answer(self):
        result, _, fake = run_with_input(["the future"], tvw_path.riddle, "Hero")
        self.assertIs(result, True)
        self.assertEqual(fake.prompts, 1)

    def test_riddle_wrong_answer_fails(self):
        result, _, fake = run_with_input(["a potato"], tvw_path.riddle, "Hero")
        self.assertIs(result, False)
        self.assertEqual(fake.prompts, 1)

    def test_riddle_empty_answer_fails_without_looping(self):
        result, _, fake = run_with_input([""], tvw_path.riddle, "Hero")
        self.assertIs(result, False)
        self.assertEqual(fake.prompts, 1)

    def test_river_success_with_fixed_seed(self):
        random.seed(5)  # first user_D20 roll with this seed is 18
        with support.narrative_cwd():
            result, _, _ = run_with_input(["roll"], tvw_path.river, "Hero", dict(DWARF))
        self.assertIs(result, True)

    def test_river_failure_with_fixed_seed(self):
        random.seed(1)  # first user_D20 roll with this seed is 5; 5 + 1 athletics <= 10
        with support.narrative_cwd():
            result, _, _ = run_with_input(["roll"], tvw_path.river, "Hero", dict(DWARF))
        self.assertIs(result, False)


class GameFlowTests(unittest.TestCase):
    def play(self, answers, **patches):
        with support.narrative_cwd(), support.patched(**patches):
            return run_with_input(answers, tvw_game.the_vengeful_wyrm)

    def test_lost_fight_does_not_advance_mission(self):
        result, output, _ = self.play(
            ["1", "Hero", "yes", "wisdom", "the future"], **LOSS_ROLLS)
        self.assertIs(result, False)
        self.assertIn("defeated", output.lower())
        self.assertNotIn("Happy end", output)

    def test_won_fight_completes_mission_once(self):
        result, output, _ = self.play(
            ["1", "Hero", "yes", "wisdom", "the future"], **WIN_ROLLS)
        self.assertIs(result, True)
        self.assertEqual(output.count("Happy end"), 1)

    def test_failed_riddle_stops_game(self):
        result, output, _ = self.play(["1", "Hero", "yes", "wisdom", "a potato"])
        self.assertIs(result, False)
        self.assertNotIn("Wyrm's Lair", output)

    def test_failed_swim_stops_game(self):
        random.seed(1)  # river skill check fails with this seed
        result, output, _ = self.play(["1", "Hero", "yes", "strength", "roll"])
        self.assertIs(result, False)
        self.assertNotIn("Wyrm's Lair", output)

    def test_declined_mission_stops_game(self):
        result, output, _ = self.play(["1", "Hero", "no", "yes"])
        self.assertIs(result, False)
        self.assertNotIn("Right Path", output)

    def test_main_reprompts_on_invalid_play_again(self):
        answers = ["1", "Hero", "no", "yes", "maybe", "no"]
        with support.narrative_cwd():
            _, output, _ = run_with_input(answers, tvw_game.main)
        self.assertIn("I did not understand", output)
        self.assertEqual(output.count("Choose your character"), 1)
        self.assertIn("Credits", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
