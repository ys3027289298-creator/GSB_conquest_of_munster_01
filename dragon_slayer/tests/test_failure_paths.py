import contextlib
import io
import os
import tempfile
import unittest

from weapons.bow import Bow
from weapons.shield import Shield
from story.state import GameState
from story.battle import battle
from story.fishing import fishing
from story.training import training

from tests.helpers import patched_game, run_main


class FishingInventoryTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.save_path = os.path.join(self.tmpdir.name, "save_game.json")

    def test_fishing_results_are_written_back_to_inventory(self):
        player = Bow("Hero")
        output = io.StringIO()
        with patched_game(["y"] * 4, self.save_path,
                          fish_items=["trash", "trout", "potion", "Dragon Ring"]):
            with contextlib.redirect_stdout(output):
                fishing(player)
        self.assertTrue(player.has_dragon_ring)
        self.assertEqual(player.potions, 1)
        self.assertIn("You found the Dragon Ring!", output.getvalue())


class TrainingRewardTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.save_path = os.path.join(self.tmpdir.name, "save_game.json")

    def test_mana_reward_is_granted_once_after_training(self):
        player = Shield("Hero")
        mana_before_round = []
        original_use_ability = player.use_ability

        def record(ability, target):
            mana_before_round.append(player.mana)
            return original_use_ability(ability, target)

        player.use_ability = record
        with patched_game(["2", "y", "2", "n"], self.save_path):
            with contextlib.redirect_stdout(io.StringIO()):
                training(player)
        self.assertEqual(mana_before_round, [100, 90])
        self.assertEqual(player.mana, 100)


class BattleOutcomeTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.save_path = os.path.join(self.tmpdir.name, "save_game.json")

    def test_battle_returns_false_and_prints_game_over_on_death(self):
        player = Shield("Hero")
        player.has_dragon_ring = True
        player.potions = 0
        output = io.StringIO()
        with patched_game(["y", "1", "1"], self.save_path,
                          dragon_abilities=["Dragonbreath"]):
            with contextlib.redirect_stdout(output):
                won = battle(player)
        self.assertFalse(won)
        self.assertFalse(player.is_alive)
        self.assertIn("=== Game Over ===", output.getvalue())

    def test_potion_revives_once_then_player_falls(self):
        player = Shield("Hero")
        player.has_dragon_ring = True
        player.potions = 1
        output = io.StringIO()
        with patched_game(["y", "1", "1", "1"], self.save_path,
                          dragon_abilities=["Dragonbreath"]):
            with contextlib.redirect_stdout(output):
                won = battle(player)
        text = output.getvalue()
        self.assertFalse(won)
        self.assertEqual(player.potions, 0)
        self.assertEqual(text.count("Drinking the potion..."), 1)
        self.assertIn("No potions found.", text)
        self.assertIn("You have fallen.", text)

    def test_dead_dragon_does_not_attack_after_death(self):
        player = Bow("Hero")
        player.has_dragon_ring = True
        output = io.StringIO()
        with patched_game(["y"] + ["3"] * 5, self.save_path,
                          dragon_abilities=["Claw"]):
            with contextlib.redirect_stdout(output):
                won = battle(player)
        text = output.getvalue()
        self.assertTrue(won)
        self.assertEqual(text.count("Oolong uses"), 4)
        last_attack = text.rfind("Oolong uses")
        kill = text.find("has 0 health remaining")
        self.assertLess(last_attack, kill)

    def test_battle_returns_true_on_victory(self):
        player = Bow("Hero")
        player.has_dragon_ring = True
        with patched_game(["y"] + ["3"] * 5, self.save_path,
                          dragon_abilities=["Claw"]):
            with contextlib.redirect_stdout(io.StringIO()):
                won = battle(player)
        self.assertTrue(won)


class PlayAgainTest(unittest.TestCase):
    def test_invalid_choice_reprompts_without_skipping_input(self):
        import builtins
        from unittest import mock
        from main import play_again

        inputs = iter(["maybe", "y"])
        with mock.patch("time.sleep", lambda *a, **k: None), \
             mock.patch.object(builtins, "input", lambda prompt="": next(inputs)):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = play_again()
        self.assertTrue(result)
        self.assertIn("Enter y or n.", output.getvalue())


class LoseAndResumeFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.save_path = os.path.join(self.tmpdir.name, "save_game.json")

    def test_losing_battle_saves_lost_node_and_retry_lands_at_battle(self):
        run_a_inputs = (["Hero", "2"] + ["1", "n"] + ["y", "y"] + ["y"]
                        + ["1", "1", "1"] + ["n"])
        output_a = run_main(run_a_inputs, self.save_path,
                            fish_items=["potion", "Dragon Ring"],
                            dragon_abilities=["Dragonbreath"])
        self.assertIn("=== Game Over ===", output_a)
        self.assertIn("Thanks for playing!", output_a)

        self.assertTrue(os.path.exists(self.save_path))
        saved = GameState.load(self.save_path)
        self.assertEqual(saved.node, "lost")
        self.assertIsInstance(saved.player, Shield)
        self.assertTrue(saved.player.is_alive)
        self.assertEqual(saved.player.health, 100)
        self.assertEqual(saved.player.potions, 1)
        self.assertTrue(saved.player.has_dragon_ring)

        run_b_inputs = ["y", "y"] + ["2"] * 10 + ["n"]
        output_b = run_main(run_b_inputs, self.save_path,
                            dragon_abilities=["Claw"])
        self.assertNotIn("Welcome to Dragon Slayer", output_b)
        self.assertNotIn("Training Dummy", output_b)
        self.assertNotIn("Go fishing?", output_b)
        self.assertIn("Are you ready to fight the dragon?", output_b)
        self.assertIn("=== Dragon Fight ===", output_b)
        self.assertIn("=== You beat the game! ===", output_b)
        self.assertFalse(os.path.exists(self.save_path))


if __name__ == "__main__":
    unittest.main()
