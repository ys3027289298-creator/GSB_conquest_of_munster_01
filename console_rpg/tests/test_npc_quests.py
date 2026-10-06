"""NPC dialogue must advance quest state (bug #4)."""
from tests.helpers import (QuietTestCase, make_game, make_game_main,
                           no_dialogue_delay)


class NPCQuestTest(QuietTestCase):

    def setUp(self):
        super().setUp()
        self.game = make_game(0)
        self.game_main = make_game_main(self.game)
        self._sleep_patch = no_dialogue_delay()
        self._sleep_patch.__enter__()
        self.addCleanup(self._sleep_patch.__exit__, None, None, None)

    def talk(self, npc):
        self.game_main.talk(npc.x)

    def test_alchemist_first_talk_advances_state(self):
        alchemist = self.game.alchemist
        self.talk(alchemist)
        self.assertEqual(self.game_main.meet_mals["Alchemist"], [0, 1])

    def test_alchemist_quest_completes(self):
        alchemist = self.game.alchemist
        self.talk(alchemist)  # introduction
        self.talk(alchemist)  # he asks for the reed
        for _ in range(5):
            self.game.player.Eq1.add_element("Reed")
        potions_before = self.game.player.Eq1.items_names().count("HP Potion")
        self.talk(alchemist)  # hands over 5 reed
        self.assertEqual(alchemist.quest, 1)
        self.assertEqual(self.game_main.meet_mals["Alchemist"][0], 2)
        self.assertNotIn("Reed", self.game.player.Eq1.items_names())
        self.assertEqual(self.game.player.Eq1.items_names().count("HP Potion"),
                         potions_before + 1)
        self.talk(alchemist)  # final thanks, state stays consistent
        self.assertEqual(self.game_main.meet_mals["Alchemist"][0], 2)

    def test_alchemist_waits_when_reed_missing(self):
        alchemist = self.game.alchemist
        self.talk(alchemist)
        self.talk(alchemist)
        self.talk(alchemist)  # not enough reed -> quest stays open
        self.assertEqual(alchemist.quest, 0)
        self.assertEqual(self.game_main.meet_mals["Alchemist"][0], 1)

    def test_guard_quest_completes(self):
        guard = self.game.guard
        self.talk(guard)
        self.talk(guard)
        # all bandits slain
        self.game.enemies_spawn.enemies[0] = []
        self.talk(guard)
        self.assertEqual(guard.quest, 1)
        self.assertEqual(self.game_main.meet_mals["Guard"][0], 2)
        self.assertIn("Silver Claymore", self.game.player.Eq1.items_names())

    def test_monk_quest_completes(self):
        monk = self.game.monk
        self.talk(monk)
        self.talk(monk)
        self.game.player.Eq1.add_element("Bone Sword")
        self.talk(monk)
        self.assertEqual(monk.quest, 1)
        self.assertEqual(self.game_main.meet_mals["Monk"][0], 2)
        self.assertNotIn("Bone Sword", self.game.player.Eq1.items_names())
        self.assertIn("Golden Key", self.game.player.Eq1.items_names())
