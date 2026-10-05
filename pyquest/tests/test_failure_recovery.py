"""Failure recovery: bad scripts report errors but never kill the game."""
import unittest

from helpers import make_and_run


class FailureRecoveryTests(unittest.TestCase):
    def test_undefined_function_call_is_reported_and_skipped(self):
        game, out, err = make_and_run(start='DoesNotExist()\nmsg("after")')
        self.assertIn("after", out)
        self.assertIn("NameError", err)
        self.assertIn("DoesNotExist", err)

    def test_missing_object_is_reported_and_skipped(self):
        game, out, err = make_and_run(start='msg(ghost.alias)\nmsg("after")')
        self.assertIn("after", out)
        self.assertIn("NameError", err)
        self.assertIn("ghost", err)

    def test_looping_event_is_aborted(self):
        # A function that calls itself forever must be stopped gracefully
        # rather than crashing the interpreter with a RecursionError.
        function = '<function name="Haunt">Haunt()</function>'
        game, out, err = make_and_run(start='Haunt()\nmsg("after")', extra=function)
        self.assertIn("after", out)
        self.assertIn("loop", err.lower())

    def test_mutually_recursive_events_are_aborted(self):
        functions = ('<function name="Ping">Pong()</function>'
                     '<function name="Pong">Ping()</function>')
        game, out, err = make_and_run(start='Ping()\nmsg("after")', extra=functions)
        self.assertIn("after", out)
        self.assertIn("loop", err.lower())

    def test_syntax_error_is_reported_and_skipped(self):
        game, out, err = make_and_run(start='this is not valid code\nmsg("after")')
        self.assertIn("after", out)
        self.assertIn("SyntaxError", err)

    def test_error_inside_if_block_does_not_kill_game(self):
        code = ('if (1 = 1) {\n'
                'msg(ghost.alias)\n'
                '}\n'
                'msg("after")')
        game, out, err = make_and_run(start=code)
        self.assertIn("after", out)
        self.assertIn("NameError", err)


if __name__ == "__main__":
    unittest.main()
