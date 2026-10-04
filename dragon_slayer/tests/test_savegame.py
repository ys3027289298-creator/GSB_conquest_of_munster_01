import os
import tempfile
import unittest

from weapons.spear import Spear
import savegame


class SaveLoadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        os.remove(self.tmp.name)
        self.path = self.tmp.name

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_load_without_save_returns_none(self):
        self.assertIsNone(savegame.load_game(self.path))
        self.assertFalse(savegame.has_saved_game(self.path))

    def test_state_round_trips_through_save_file(self):
        player = Spear("Sigurd")
        player.add_item("Dragon Ring")
        player.add_item("potion")
        player.add_item("bass")
        player.health = 62
        player.mana = 47
        player.training_reward_claimed = True
        savegame.save_game(player, "battle", path=self.path)
        self.assertTrue(savegame.has_saved_game(self.path))

        loaded, stage = savegame.load_game(self.path)
        self.assertIsInstance(loaded, Spear)
        self.assertEqual(loaded.name, "Sigurd")
        self.assertEqual(loaded.health, 62)
        self.assertEqual(loaded.mana, 47)
        self.assertEqual(loaded.potions, 1)
        self.assertTrue(loaded.has_dragon_ring)
        self.assertTrue(loaded.training_reward_claimed)
        self.assertEqual(loaded.inventory["bass"], 1)
        self.assertEqual(stage, "battle")

    def test_clear_save_removes_file(self):
        player = Spear("Sigurd")
        savegame.save_game(player, "fishing", path=self.path)
        savegame.clear_save(self.path)
        self.assertFalse(os.path.exists(self.path))


if __name__ == "__main__":
    unittest.main()
