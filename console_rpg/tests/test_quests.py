"""Bug 4: NPC dialogue must advance quest state instead of crashing."""
import unittest
import unittest.mock

import game.Game_Engine as GameEngineModule
from tests.helpers import make_game_main, quiet

from game.data.characters.equipment.Items import Item


def fast_talk(game_main, x):
    with unittest.mock.patch.object(GameEngineModule, "sleep", lambda *a: None):
        return quiet(game_main.talk, x)


class TestAlchemistQuest(unittest.TestCase):
    def test_dialogue_has_initial_state_marker(self):
        game_main = make_game_main(0)
        self.assertEqual(game_main.game_now.alchemist.dialogues[0], 0)

    def test_talk_advances_quest_state(self):
        game_main = make_game_main(0)
        alchemist = game_main.game_now.alchemist
        self.assertEqual(game_main.meet_mals["Alchemist"], [0, 0])
        fast_talk(game_main, alchemist.x)   # first meeting: quest is given
        self.assertEqual(game_main.meet_mals["Alchemist"], [0, 1])
        fast_talk(game_main, alchemist.x)   # state advances on the next talk
        self.assertEqual(game_main.meet_mals["Alchemist"], [1, 1])

    def test_exactly_five_reeds_complete_quest(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        game.player.Eq1.elements = [Item("Reed") for _ in range(5)]
        quiet(game_main.quest_alchemist)
        self.assertEqual(game.alchemist.quest, 1)
        self.assertEqual(game_main.meet_mals["Alchemist"][0], 2)
        self.assertEqual([i.name for i in game.player.Eq1.elements],
                         ["HP Potion"])

    def test_full_alchemist_quest_line(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        alchemist = game.alchemist
        fast_talk(game_main, alchemist.x)
        fast_talk(game_main, alchemist.x)
        for _ in range(5):
            game.player.Eq1.add_element("Reed")
        fast_talk(game_main, alchemist.x)   # hands over the reeds
        self.assertEqual(game.alchemist.quest, 1)
        self.assertEqual(game_main.meet_mals["Alchemist"], [2, 1])
        self.assertIn("HP Potion", game.player.Eq1.items_names())
        self.assertNotIn("Reed", game.player.Eq1.items_names())


class TestGuardAndMonkQuests(unittest.TestCase):
    def test_guard_quest_progression(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        guard = game.guard
        fast_talk(game_main, guard.x)
        fast_talk(game_main, guard.x)
        self.assertEqual(game_main.meet_mals["Guard"], [1, 1])
        game.enemies_spawn.enemies[0] = []  # all bandits dead
        fast_talk(game_main, guard.x)
        self.assertEqual(game.guard.quest, 1)
        self.assertEqual(game_main.meet_mals["Guard"], [2, 1])
        self.assertIn("Silver Claymore", game.player.Eq1.items_names())

    def test_monk_quest_progression(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        monk = game.monk
        fast_talk(game_main, monk.x)
        fast_talk(game_main, monk.x)
        game.player.Eq1.add_element("Bone Sword")
        fast_talk(game_main, monk.x)
        self.assertEqual(game.monk.quest, 1)
        self.assertEqual(game_main.meet_mals["Monk"], [2, 1])
        self.assertIn("Golden Key", game.player.Eq1.items_names())
        self.assertNotIn("Bone Sword", game.player.Eq1.items_names())


if __name__ == "__main__":
    unittest.main()
