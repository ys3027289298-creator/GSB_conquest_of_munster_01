import os
import tempfile
import unittest

from story import state
from story.state import GameState
from weapons.bow import Bow
from weapons.shield import Shield

from tests.helpers import run_main


class TransitionTest(unittest.TestCase):
    def test_story_nodes_advance_in_order(self):
        self.assertEqual(state.next_node(state.INTRO), state.TRAINING)
        self.assertEqual(state.next_node(state.TRAINING), state.FISHING)
        self.assertEqual(state.next_node(state.FISHING), state.BATTLE)
        self.assertEqual(state.next_node(state.BATTLE), state.WON)

    def test_lost_transitions_back_to_battle(self):
        self.assertEqual(state.next_node(state.LOST), state.BATTLE)

    def test_new_game_starts_at_training(self):
        player = Bow("Hero")
        game_state = GameState.new_game(player)
        self.assertEqual(game_state.node, state.TRAINING)
        self.assertIs(game_state.player, player)

    def test_advance_walks_the_whole_story(self):
        game_state = GameState.new_game(Bow("Hero"))
        visited = [game_state.node]
        while game_state.node != state.WON:
            game_state.advance()
            visited.append(game_state.node)
        self.assertEqual(visited, [state.TRAINING, state.FISHING, state.BATTLE, state.WON])


class PersistenceTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.save_path = os.path.join(self.tmpdir.name, "save_game.json")

    def test_save_load_roundtrip_preserves_player(self):
        player = Shield("Hero")
        player.health = 65
        player.mana = 40
        player.potions = 2
        player.has_dragon_ring = True
        GameState(state.BATTLE, player).save(self.save_path)

        loaded = GameState.load(self.save_path)
        self.assertEqual(loaded.node, state.BATTLE)
        self.assertIsInstance(loaded.player, Shield)
        self.assertEqual(loaded.player.name, "Hero")
        self.assertEqual(loaded.player.health, 65)
        self.assertEqual(loaded.player.mana, 40)
        self.assertEqual(loaded.player.potions, 2)
        self.assertTrue(loaded.player.has_dragon_ring)
        self.assertTrue(loaded.player.is_alive)

    def test_exists_and_clear(self):
        self.assertFalse(GameState.exists(self.save_path))
        GameState(state.FISHING, Bow("Hero")).save(self.save_path)
        self.assertTrue(GameState.exists(self.save_path))
        GameState.clear(self.save_path)
        self.assertFalse(GameState.exists(self.save_path))


class ResumeFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.save_path = os.path.join(self.tmpdir.name, "save_game.json")

    def test_resume_from_fishing_skips_intro_and_training(self):
        player = Bow("Hero")
        GameState(state.FISHING, player).save(self.save_path)
        inputs = ["y"] + ["y", "y"] + ["y"] + ["3"] * 5 + ["n"]
        output = run_main(inputs, self.save_path,
                          fish_items=["potion", "Dragon Ring"],
                          dragon_abilities=["Claw"])
        self.assertNotIn("Welcome to Dragon Slayer", output)
        self.assertNotIn("Training Dummy", output)
        self.assertIn("Fishing...", output)
        self.assertIn("=== You beat the game! ===", output)
        self.assertFalse(os.path.exists(self.save_path))

    def test_declining_continue_starts_fresh_and_clears_save(self):
        GameState(state.FISHING, Bow("Hero")).save(self.save_path)
        inputs = ["n"] + ["Hero", "1"] + ["3", "n"] + ["y", "y"] + ["y"] + ["3"] * 5 + ["n"]
        output = run_main(inputs, self.save_path,
                          fish_items=["potion", "Dragon Ring"],
                          dragon_abilities=["Claw"])
        self.assertIn("Welcome to Dragon Slayer", output)
        self.assertIn("=== You beat the game! ===", output)
        self.assertFalse(os.path.exists(self.save_path))

    def test_winning_run_clears_save(self):
        inputs = ["Hero", "1"] + ["3", "n"] + ["y", "y"] + ["y"] + ["3"] * 5 + ["n"]
        output = run_main(inputs, self.save_path,
                          fish_items=["potion", "Dragon Ring"],
                          dragon_abilities=["Claw"])
        self.assertIn("=== You beat the game! ===", output)
        self.assertIn("Thanks for playing!", output)
        self.assertFalse(os.path.exists(self.save_path))


if __name__ == "__main__":
    unittest.main()
