"""Replay: the startup event fires once and reset() restores the initial world."""
import unittest

from helpers import make_game, make_and_run, run_game

SWORD = ('<object name="sword">'
         '<alias>Iron Sword</alias>'
         '<damage>5</damage>'
         '</object>')

LOOK = ('<function name="Look">firsttime {\n'
        'msg("first")\n'
        '}\n'
        'otherwise {\n'
        'msg("later")\n'
        '}</function>')


class ReplayTests(unittest.TestCase):
    def test_startup_event_runs_once_per_playthrough(self):
        game = make_game(start='msg("once")')
        out1, err1 = run_game(game)
        out2, err2 = run_game(game)  # must not execute the event again
        self.assertEqual((out1 + out2).count("once"), 1)
        self.assertEqual(err1, "")
        self.assertEqual(err2, "")

    def test_reset_allows_the_game_to_be_played_again(self):
        game = make_game(start='msg("start")')
        out1, _ = run_game(game)
        game.reset()
        out2, _ = run_game(game)
        self.assertEqual(out1.count("start"), 1)
        self.assertEqual(out2.count("start"), 1)

    def test_replay_restores_object_attributes(self):
        game, out, err = make_and_run(start="sword.damage = 7", extra=SWORD)
        self.assertEqual(game.objects["sword"].damage, 7)
        game.reset()
        self.assertEqual(str(game.objects["sword"].damage), "5")
        # The startup event re-executes on the replayed run.
        run_game(game)
        self.assertEqual(game.objects["sword"].damage, 7)

    def test_replay_re_fires_firsttime_events(self):
        game = make_game(start="Look()", extra=LOOK)
        out1, _ = run_game(game)
        self.assertIn("first", out1)
        self.assertNotIn("later", out1)
        game.reset()
        out2, _ = run_game(game)
        self.assertIn("first", out2)
        self.assertNotIn("later", out2)

    def test_replay_clears_script_variables(self):
        game, out, err = make_and_run(start="score = 42")
        self.assertEqual(game.script_engine.namespace["score"], 42)
        game.reset()
        self.assertNotIn("score", game.script_engine.namespace)

    def test_replay_does_not_leak_into_other_games(self):
        game1, out1, err1 = make_and_run(start="score = 1")
        game2, out2, err2 = make_and_run(start="score = 2")
        game1.reset()
        self.assertNotIn("score", game1.script_engine.namespace)
        self.assertEqual(game2.script_engine.namespace["score"], 2)


if __name__ == "__main__":
    unittest.main()
