"""Narrator loop tests: abnormal input handling, path validation at the
command layer, and preservation of the original teaching text."""
import unittest
from unittest import mock

from tests.helpers import SandboxCase, run_silently

import commands
import narrator


def feed_inputs(testcase, root, inputs):
    """Run the narrate loop over scripted input lines (quit appended);
    returns everything printed, including input() prompts."""
    import io
    from contextlib import redirect_stdout
    state = narrator.GameState(root)
    script = iter(inputs + ['quit'])

    def fake_input(prompt=''):
        print(prompt, end='')
        return next(script)

    buffer = io.StringIO()
    with mock.patch('builtins.input', fake_input):
        with redirect_stdout(buffer):
            with testcase.assertRaises(SystemExit) as ctx:
                narrator.narrate(state)
    testcase.assertEqual(0, ctx.exception.code)
    return buffer.getvalue()


class AbnormalInputLoopTest(SandboxCase):
    """Bug reproduced: an empty command crashed the input loop."""

    def feed(self, inputs):
        return feed_inputs(self, self.root, inputs)

    def test_empty_and_blank_input(self):
        output = self.feed(['', '   ', '\t'])
        self.assertIn('Goodbye!', output)

    def test_garbage_input(self):
        output = self.feed(['xyzzy', '!@#$', '...'])
        self.assertIn('Goodbye!', output)

    def test_mixed_case_and_spacing_commands(self):
        output = self.feed(['  LOOK ', 'HeLp', 'WHERE'])
        self.assertIn('You can go: ', output)
        self.assertIn('Feeling lost?', output)
        self.assertIn("Haha, this is embarrassing", output)

    def test_go_without_target_asks_and_recovers(self):
        output = self.feed(['go', 'look'])
        self.assertIn('Where do you want to move?', output)


class PathValidationCommandTest(SandboxCase):
    """Bug reproduced: `go` could escape the sandbox or crash on bad
    targets; now it must refuse cleanly."""

    def test_go_escape_is_refused(self):
        state = narrator.GameState(self.root)
        _, output = run_silently(commands.execute_command, 'go', state,
                                 'go ..', '..')
        self.assertIn(commands.MSG_CANNOT_GO, output)
        self.assertEqual(state.vfs.root, state.vfs.cwd)

    def test_go_to_missing_dir_is_refused(self):
        state = narrator.GameState(self.root)
        _, output = run_silently(commands.execute_command, 'go', state,
                                 'go nowhere', 'nowhere')
        self.assertIn(commands.MSG_NOT_A_PLACE, output)

    def test_go_onto_file_is_refused(self):
        state = narrator.GameState(self.root)
        state.vfs.cd('alpha')
        _, output = run_silently(commands.execute_command, 'go', state,
                                 'go note.txt', 'note.txt')
        self.assertIn(commands.MSG_NOT_A_PLACE, output)

    def test_go_target_matching_is_case_insensitive(self):
        state = narrator.GameState(self.root)
        run_silently(commands.execute_command, 'go', state, 'go ALPHA',
                     'ALPHA')
        self.assertIn('alpha', state.vfs.cwd)

    def test_go_with_extra_whitespace_target(self):
        state = narrator.GameState(self.root)
        run_silently(commands.execute_command, 'go', state,
                     'go    beta   ', 'beta')
        self.assertIn('beta', state.vfs.cwd)


class TeachingTextTest(SandboxCase):
    """The original teaching text must remain untouched."""

    def test_welcome_and_quit_text(self):
        output = feed_inputs(self, self.root, [])
        self.assertIn("Welcome! Type '", output)
        self.assertIn("' at any time to stop the program. Type '", output)
        self.assertIn("' to see your options.", output)
        self.assertIn('Goodbye!', output)

    def test_help_text(self):
        _, output = run_silently(commands.execute_help)
        self.assertIn('Feeling lost? Available commands are:', output)
        self.assertIn('look at current directory', output)
        self.assertIn('move to another directory', output)
        self.assertIn('exit to the command line', output)

    def test_inventory_text(self):
        _, output = run_silently(commands.execute_inventory)
        self.assertEqual(
            'You check your inventory. You have: a stick of gum, a '
            'business card, a pair of scissors. I have not programmed '
            'any actions you can take with any of these items.\n', output)

    def test_where_text(self):
        state = narrator.GameState(self.root)
        _, output = run_silently(commands.execute_command, 'where', state)
        self.assertIn("Haha, this is embarrassing, I haven't coded that yet.",
                      output)

    def test_look_text(self):
        state = narrator.GameState(self.root)
        _, output = run_silently(commands.execute_command, 'look', state,
                                 'look', None)
        self.assertIn('You can go: ', output)
        state.vfs.cd('beta')
        _, output = run_silently(commands.execute_command, 'look', state,
                                 'look', None)
        self.assertIn('There are no files here.', output)
        self.assertIn('You can go: back the way you came', output)


if __name__ == '__main__':
    unittest.main()
