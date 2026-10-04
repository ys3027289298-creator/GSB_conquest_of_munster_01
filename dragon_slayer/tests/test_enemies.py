import unittest
from unittest.mock import patch, MagicMock

from weapons.bow import Bow
from enemies.dragon import Dragon
from story.battle import fight_dragon
from tests.helpers import no_sleep


class EnemyDeathTests(unittest.TestCase):
    def setUp(self):
        no_sleep().start()

    def tearDown(self):
        patch.stopall()

    def test_dead_dragon_does_not_attack(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        dragon.is_alive = False
        dragon.use_ability("Claw", player)
        self.assertEqual(player.health, 100)

    def test_dead_player_is_not_attacked(self):
        player = Bow("Hero")
        player.is_alive = False
        dragon = Dragon("Oolong")
        dragon.use_ability("Claw", player)
        self.assertEqual(player.health, 100)

    @patch("story.battle.get_ability_choice", return_value="Attack")
    @patch("story.battle.use_potion")
    def test_killing_blow_prevents_dragon_counterattack(self, _potion, _choice):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        dragon.health = 5
        dragon.use_ability = MagicMock(wraps=dragon.use_ability)
        fight_dragon(player, dragon)
        self.assertFalse(dragon.is_alive)
        dragon.use_ability.assert_not_called()
        self.assertTrue(player.is_alive)


if __name__ == "__main__":
    unittest.main()
