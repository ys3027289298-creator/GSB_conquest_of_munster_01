import unittest
from unittest.mock import patch

from weapons.bow import Bow
from story import fishing as fishing_module
from tests.helpers import no_sleep


class FishingInventoryTests(unittest.TestCase):
    def setUp(self):
        no_sleep().start()
        self.player = Bow("Hero")

    def tearDown(self):
        patch.stopall()

    def test_ring_is_written_back_to_inventory(self):
        fishing_module.go_fishing(self.player, "Dragon Ring")
        self.assertTrue(self.player.has_dragon_ring)
        self.assertEqual(self.player.inventory["Dragon Ring"], 1)

    def test_potion_is_written_back_to_inventory(self):
        fishing_module.go_fishing(self.player, "potion")
        self.assertEqual(self.player.potions, 1)
        self.assertEqual(self.player.inventory["potion"], 1)

    def test_fish_catch_is_written_back_to_inventory(self):
        fishing_module.go_fishing(self.player, "trout")
        self.assertEqual(self.player.inventory["trout"], 1)

    def test_handle_fishing_loops_until_requirements_met(self):
        catches = ["trash", "potion", "bass", "Dragon Ring"]
        with patch("story.fishing.get_fishing_choice"), \
             patch("story.fishing.get_random_item", side_effect=catches):
            fishing_module.handle_fishing(self.player)
        self.assertTrue(self.player.has_dragon_ring)
        self.assertEqual(self.player.potions, 1)
        self.assertEqual(self.player.inventory["trash"], 1)
        self.assertEqual(self.player.inventory["bass"], 1)


if __name__ == "__main__":
    unittest.main()
