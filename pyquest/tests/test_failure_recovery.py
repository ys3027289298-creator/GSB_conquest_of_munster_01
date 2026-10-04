"""失败恢复: undefined jumps, missing objects and safe script execution."""
from tests.util import GameTestCase

from pyquest.errors import MissingObjectError, ScriptError, UndefinedJumpError
from pyquest.script_engine import Script



class UndefinedJumpTests(GameTestCase):
    def test_call_to_undefined_function_raises(self):
        with self.assertRaises(UndefinedJumpError) as ctx:
            self.run_script("GoToHall ()")
        self.assertEqual(ctx.exception.target, "GoToHall")

    def test_undefined_jump_is_a_script_error(self):
        with self.assertRaises(ScriptError):
            self.run_script("Nowhere ()")


class MissingObjectTests(GameTestCase):
    def test_get_object_raises(self):
        with self.assertRaises(MissingObjectError) as ctx:
            self.game.get_object("ghost")
        self.assertEqual(ctx.exception.object_name, "ghost")

    def test_getobject_builtin_raises(self):
        with self.assertRaises(MissingObjectError):
            self.run_script("GetObject (\"ghost\")")

    def test_failed_move_does_not_mutate_world(self):
        sword = self.game.objects["sword"]
        before = sword.parent
        with self.assertRaises(MissingObjectError):
            self.run_script("MoveObject (sword, \"nowhere\")")
        self.assertIs(sword.parent, before)

    def test_move_object_by_name(self):
        self.run_script("MoveObject (sword, hall)")
        self.assertIs(self.game.objects["sword"].parent, self.game.objects["hall"])


class RecoveryTests(GameTestCase):
    def test_run_safe_captures_error_and_recovers(self):
        engine = self.game.script_engine
        err = engine.run_safe(Script("bad", "GoToHall ()"))
        self.assertIsInstance(err, UndefinedJumpError)
        self.assertIs(self.game.last_error, err)
        # the engine is still usable afterwards
        _, out = self.run_script("msg (\"still alive\")")
        self.assertIn("still alive", out)

    def test_run_safe_returns_none_on_success(self):
        engine = self.game.script_engine
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(engine.run_safe(Script("ok", "msg (\"fine\")")))

    def test_run_safe_wraps_unresolved_names(self):
        engine = self.game.script_engine
        err = engine.run_safe(Script("bad", "player.gold = missing_thing + 1"))
        self.assertIsInstance(err, ScriptError)

    def test_runaway_loop_is_aborted(self):
        from pyquest.script_engine import MAX_LOOP_ITERATIONS
        err = self.game.script_engine.run_safe(
            Script("loop", "while (true) {\n  player.gold = player.gold + 0\n}"))
        self.assertIsInstance(err, ScriptError)
        self.assertIn(str(MAX_LOOP_ITERATIONS), str(err))

    def test_error_in_one_script_does_not_skip_event_bookkeeping(self):
        # a failed script must not mark unrelated firsttime events as done
        self.game.script_engine.run_safe(Script("bad", "GoToHall ()"))
        _, out = self.call_function("EnterHall")
        self.assertIn("first time", out)
