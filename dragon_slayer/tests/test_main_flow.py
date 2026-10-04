import unittest
from unittest.mock import patch, MagicMock

from weapons.bow import Bow
from story.state import INTRO, FISHING, BATTLE, VICTORY, GAME_OVER
import main


class StoryFlowTests(unittest.TestCase):
    def setUp(self):
        self.player = Bow("Hero")
        self.saved_stages = []

    def _record_save(self):
        def record(player, stage, **_kwargs):
            self.saved_stages.append(stage)
        return MagicMock(side_effect=record)

    @patch.object(main, "savegame")
    @patch.object(main, "battle")
    def test_defeat_routes_to_game_over_node(self, mock_battle, mock_savegame):
        mock_battle.return_value = False
        mock_savegame.save_game.side_effect = self._record_save()
        with patch.object(main, "ask_retry_battle", return_value=False):
            stage = main.run_story(self.player, BATTLE)
        self.assertEqual(stage, GAME_OVER)
        self.assertEqual(self.saved_stages[-1], GAME_OVER)

    @patch.object(main, "savegame")
    @patch.object(main, "battle")
    def test_defeat_then_retry_revives_and_reaches_victory(self, mock_battle, mock_savegame):
        mock_battle.side_effect = [False, True]
        mock_savegame.save_game.side_effect = self._record_save()
        with patch.object(main, "ask_retry_battle", return_value=True):
            stage = main.run_story(self.player, BATTLE)
        self.assertEqual(stage, VICTORY)
        self.assertTrue(self.player.is_alive)
        self.assertEqual(self.player.health, 100)
        self.assertIn(GAME_OVER, self.saved_stages)

    @patch.object(main, "savegame")
    @patch.object(main, "battle", return_value=True)
    def test_intro_runs_nodes_in_order(self, _mock_battle, mock_savegame):
        mock_savegame.save_game.side_effect = self._record_save()
        with patch.dict(main.STAGE_HANDLERS,
                        {"training": MagicMock(), "fishing": MagicMock()}):
            stage = main.run_story(self.player, INTRO)
        self.assertEqual(stage, VICTORY)
        self.assertEqual(self.saved_stages[0], "training")
        self.assertEqual(self.saved_stages[-1], VICTORY)

    @patch.object(main, "savegame")
    @patch.object(main, "battle", return_value=True)
    def test_resuming_skips_completed_nodes(self, _mock_battle, mock_savegame):
        mock_savegame.save_game.side_effect = self._record_save()
        mock_training = MagicMock()
        mock_fishing = MagicMock()
        with patch.dict(main.STAGE_HANDLERS,
                        {"training": mock_training, "fishing": mock_fishing}):
            stage = main.run_story(self.player, FISHING)
        self.assertEqual(stage, VICTORY)
        mock_training.assert_not_called()
        mock_fishing.assert_called_once_with(self.player)


if __name__ == "__main__":
    unittest.main()
