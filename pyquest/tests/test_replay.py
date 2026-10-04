"""重玩: restarting a playthrough resets world and event state."""
from tests.util import GameTestCase



class ReplayTests(GameTestCase):
    def test_restart_resets_player_state(self):
        self.player.gold = 99
        self.game.restart()
        self.assertEqual(str(self.game.objects["player"].gold), "5")

    def test_restart_resets_object_locations(self):
        self.game.objects["sword"].parent = self.game.objects["hall"]
        self.game.restart()
        self.assertIs(self.game.objects["sword"].parent,
                      self.game.objects["cave"])

    def test_restart_rebuilds_world_objects(self):
        self.game.restart()
        self.assertEqual(set(self.game.objects),
                         {"game", "cave", "player", "sword", "hall", "bell"})

    def test_event_fires_first_time_branch_again_after_restart(self):
        _, first = self.call_function("EnterHall")
        _, second = self.call_function("EnterHall")
        self.assertIn("first time", first)
        self.assertIn("again", second)
        self.game.restart()
        _, third = self.call_function("EnterHall")
        self.assertIn("first time", third)

    def test_functions_still_registered_after_restart(self):
        self.game.restart()
        self.call_function("AddGold", 4)
        self.assertEqual(str(self.game.objects["player"].gold), "9")

    def test_restart_clears_recorded_errors(self):
        from pyquest.script_engine import Script
        self.game.script_engine.run_safe(Script("bad", "GoToHall ()"))
        self.assertIsNotNone(self.game.last_error)
        self.game.restart()
        self.assertIsNone(self.game.last_error)

    def test_save_load_roundtrip_across_restart(self):
        self.player.gold = 42
        self.call_function("EnterHall")
        state = self.game.save_state()
        self.game.restart()
        self.game.load_state(state)
        self.assertEqual(str(self.game.objects["player"].gold), "42")
        _, out = self.call_function("EnterHall")
        self.assertIn("again", out)

    def test_run_after_restart(self):
        import contextlib
        import io
        self.game.restart()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.game.run()
        self.assertIn("Welcome to TestGame", out.getvalue())
