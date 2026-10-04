import unittest
from unittest.mock import patch

from weapons.bow import Bow
from story import training as training_module
from tests.helpers import no_sleep


class TrainingRewardTests(unittest.TestCase):
    def setUp(self):
        no_sleep().start()
        self.player = Bow("Hero")

    def tearDown(self):
        patch.stopall()

    def test_training_reward_is_granted_once(self):
        self.player.mana = 40
        training_module.grant_training_reward(self.player)
        self.assertEqual(self.player.mana, 100)
        self.assertTrue(self.player.training_reward_claimed)
        self.player.mana = 50
        training_module.grant_training_reward(self.player)
        self.assertEqual(self.player.mana, 50)

    def test_fighting_dummy_does_not_refill_mana_each_round(self):
        dummy = training_module.create_dummy()
        self.player.use_ability = lambda *_args: setattr(self.player, "mana", self.player.mana - 10)
        training_module.fight_dummy(self.player, "Power Shot", dummy)
        self.assertEqual(self.player.mana, 90)

    @patch("story.training.get_ability_choice", side_effect=["Power Shot", "Power Shot"])
    @patch("builtins.input", side_effect=["y", "n"])
    def test_full_training_session_rewards_once_at_the_end(self, _inputs, _choices):
        training_module.training(self.player)
        self.assertEqual(self.player.mana, 100)
        self.assertTrue(self.player.training_reward_claimed)


if __name__ == "__main__":
    unittest.main()
