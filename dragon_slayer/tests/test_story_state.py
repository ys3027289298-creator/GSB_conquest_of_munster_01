import unittest

from story.state import (
    INTRO,
    TRAINING,
    FISHING,
    BATTLE,
    VICTORY,
    GAME_OVER,
    next_stage,
    after_battle,
)


class StoryStateTests(unittest.TestCase):
    def test_stages_advance_in_order(self):
        self.assertEqual(next_stage(INTRO), TRAINING)
        self.assertEqual(next_stage(TRAINING), FISHING)
        self.assertEqual(next_stage(FISHING), BATTLE)
        self.assertEqual(next_stage(BATTLE), VICTORY)

    def test_battle_result_routes_correct_node(self):
        self.assertEqual(after_battle(True), VICTORY)
        self.assertEqual(after_battle(False), GAME_OVER)


if __name__ == "__main__":
    unittest.main()
