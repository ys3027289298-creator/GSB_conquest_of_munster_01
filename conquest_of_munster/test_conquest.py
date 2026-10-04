import contextlib
import io
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import engine

GAME_FILES = ['template.py', 'menu_template.py', 'dragonslayer.py']

# Full template.py playthrough: enter past every text line, pick option 0 until the end.
TEMPLATE_PLAY_INPUT = (
    "\n\n0\n"      # page 1 -> page 2
    "\n\n\n0\n"    # page 2 -> page 3
    "\n0\n"        # page 3 -> page 4
    "\n0\n"        # page 4 -> page 5
    "\n\n"         # page 5, story ends
)

# Wrapper used to run the interactive scripts in tests with the typing delay disabled.
NO_SLEEP_WRAPPER = (
    "import time; time.sleep = lambda *a, **k: None; "
    "exec(compile(open(%r).read(), %r, 'exec'))"
)


def run_script(workdir, script_name, stdin_text, timeout=60):
    code = NO_SLEEP_WRAPPER % (script_name, script_name)
    return subprocess.run(
        [sys.executable, '-c', code],
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=workdir,
        timeout=timeout,
    )


class WorkspaceTestCase(unittest.TestCase):
    """Runs real scripts in a fresh temporary copy of the game directory."""

    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        for name in ['template.py', 'menu_template.py', 'dragonslayer.py',
                     'engine.py', 'menu_engine.py']:
            shutil.copy(os.path.join(HERE, name), os.path.join(self.workdir, name))

    def tearDown(self):
        shutil.rmtree(self.workdir, ignore_errors=True)

    def load_chapter(self):
        with open(os.path.join(self.workdir, 'current_game.ch'), 'rb') as chapter:
            return pickle.load(chapter)


class TemplateParsingTests(WorkspaceTestCase):

    def test_each_game_file_builds_a_valid_chapter(self):
        for game_file in GAME_FILES:
            result = run_script(self.workdir, game_file, '')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(result.stderr, ('', None))

            chapter_path = os.path.join(self.workdir, 'current_game.ch')
            self.assertTrue(os.path.exists(chapter_path), game_file)
            story = self.load_chapter()

            self.assertIsInstance(story, dict)
            self.assertTrue(story)
            self.assertIn(1, story, 'stories must start at page 1')
            for page_number, page in story.items():
                self.assertIsInstance(page, dict, (game_file, page_number))
                self.assertIsInstance(page['Text'], list, (game_file, page_number))
                self.assertIsInstance(page['Options'], list, (game_file, page_number))
                for label, target in page['Options']:
                    self.assertIsInstance(label, str, (game_file, page_number))
                    self.assertIn(target, story,
                                  '%s page %s points to missing page %s'
                                  % (game_file, page_number, target))

    def test_death_pages_offer_no_way_to_continue(self):
        run_script(self.workdir, 'dragonslayer.py', '')
        story = self.load_chapter()
        for page_number, page in story.items():
            if any('THE END' in line for line in page['Text']):
                self.assertEqual(page['Options'], [],
                                 'death page %s must not allow continuing' % page_number)


class EngineUnitTests(unittest.TestCase):

    def setUp(self):
        self.inputs = mock.patch('builtins.input', side_effect=list())
        self.input_mock = self.inputs.start()
        self.addCleanup(self.inputs.stop)
        self.sleep = mock.patch('time.sleep')
        self.sleep.start()
        self.addCleanup(self.sleep.stop)
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def feed(self, values):
        self.input_mock.side_effect = values

    def play(self, story):
        return engine.play_story(story)

    def test_empty_chapter_does_not_crash(self):
        self.play({})
        self.assertEqual(self.input_mock.call_count, 0)

    def test_missing_text_field_is_treated_as_empty(self):
        self.feed(['0'])
        story = {1: {'Options': [('go', 2)]}, 2: {'Options': []}}
        self.play(story)

    def test_missing_options_field_ends_the_story(self):
        self.feed([''])
        self.play({1: {'Text': ['the end']}})
        self.assertEqual(self.input_mock.call_count, 1)

    def test_page_missing_both_fields_ends_the_story(self):
        self.play({1: {}})
        self.assertEqual(self.input_mock.call_count, 0)

    def test_looping_chapter_exits_cleanly_when_input_closes(self):
        self.feed(['', '0', '', '0', EOFError()])
        story = {1: {'Text': ['again?'], 'Options': [('again', 1)]}}
        with self.assertRaises(SystemExit) as caught:
            self.play(story)
        self.assertEqual(caught.exception.code, 0)

    def test_invalid_input_is_rejected_without_changing_state(self):
        self.feed(['garbage', ''])
        self.assertEqual(engine.get_user_input(['']), '')
        self.assertEqual(self.input_mock.call_count, 2)
        self.assertIn('Invalid input', self.output.getvalue())

    def test_invalid_option_number_does_not_skip_pages(self):
        self.feed(['9', 'x', '1'])
        target = engine.create_response([('first', 10), ('second', 20)])
        self.assertEqual(target, 20)


class DragonFailureTests(WorkspaceTestCase):

    def setUp(self):
        super().setUp()
        run_script(self.workdir, 'dragonslayer.py', '')
        self.story = self.load_chapter()

    def play_path(self, answers):
        with mock.patch('time.sleep'), \
                contextlib.redirect_stdout(io.StringIO()), \
                mock.patch('builtins.input', side_effect=answers) as input_mock:
            engine.play_story(self.story)
            return input_mock.call_count

    def test_dragon_belly_death_ends_the_game(self):
        # 1 -> 2 -> 12 (trail) -> 3 (hills) -> 16 (climb down) -> 11 (belly, death)
        answers = (
            ['', '', '', '0']          # page 1 -> 2
            + ['', '', '2']            # page 2 -> 12
            + ['', '', '', '', '0']   # page 12 -> 3
            + ['', '', '', '0']        # page 3 -> 16
            + [''] * 6 + ['1']         # page 16 -> 11
            + [''] * 5                 # page 11 death text, game ends
        )
        calls = self.play_path(answers)
        self.assertEqual(calls, len(answers),
                         'no input may be requested after the player has failed')

    def test_windy_cave_death_ends_the_game(self):
        # 1 -> 2 -> 8 (windy cave, immediate death)
        answers = (
            ['', '', '', '0']          # page 1 -> 2
            + ['', '', '1']            # page 2 -> 8
            + [''] * 3                 # page 8 death text, game ends
        )
        calls = self.play_path(answers)
        self.assertEqual(calls, len(answers))


class EngineScriptTests(WorkspaceTestCase):

    def test_missing_chapter_file_fails_cleanly(self):
        result = run_script(self.workdir, 'engine.py', '')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn('No valid game file', result.stdout)

    def test_empty_chapter_file_fails_cleanly(self):
        open(os.path.join(self.workdir, 'current_game.ch'), 'wb').close()
        result = run_script(self.workdir, 'engine.py', '')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)

    def test_corrupt_chapter_file_fails_cleanly(self):
        with open(os.path.join(self.workdir, 'current_game.ch'), 'wb') as chapter:
            chapter.write(b'this is not a chapter')
        result = run_script(self.workdir, 'engine.py', '')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)

    def test_looping_chapter_with_finite_input_exits_cleanly(self):
        looping_story = {1: {'Text': ['round and round'], 'Options': [('again', 1)]}}
        with open(os.path.join(self.workdir, 'current_game.ch'), 'wb') as chapter:
            pickle.dump(looping_story, chapter)
        result = run_script(self.workdir, 'engine.py', '\n0\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_repeated_runs_are_identical(self):
        run_script(self.workdir, 'template.py', '')
        first = run_script(self.workdir, 'engine.py', TEMPLATE_PLAY_INPUT)
        second = run_script(self.workdir, 'engine.py', TEMPLATE_PLAY_INPUT)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertIn('Have fun creating your stories!', first.stdout)


class MenuStateMachineTests(WorkspaceTestCase):

    MENU = 'menu_engine.py'

    def test_non_numeric_input_is_rejected_then_quit_works(self):
        result = run_script(self.workdir, self.MENU, 'abc\n3\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Please enter valid options only', result.stdout)
        self.assertIn('You have chosen to finish the game thanks for playing', result.stdout)

    def test_out_of_range_number_does_not_swallow_next_choice(self):
        # Before the fix the '2' typed after the bad number was read by the
        # out-of-range re-prompt and silently discarded.
        result = run_script(self.workdir, self.MENU, '9\n2\n3\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Please enter valid options only', result.stdout)
        self.assertIn('Please Select Option 1 and load valid game file', result.stdout)
        self.assertIn('You have chosen to finish the game thanks for playing', result.stdout)

    def test_starting_without_a_loaded_game_is_refused(self):
        result = run_script(self.workdir, self.MENU, '2\n3\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Please Select Option 1 and load valid game file', result.stdout)

    def test_missing_game_file_recovers_and_stays_in_menu(self):
        result = run_script(self.workdir, self.MENU, '1\nnope.py\n2\n3\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('That game file does not exist', result.stdout)
        self.assertIn('Please Select Option 1 and load valid game file', result.stdout)
        self.assertIn('You have chosen to finish the game thanks for playing', result.stdout)

    def test_broken_game_file_does_not_pollute_state(self):
        with open(os.path.join(self.workdir, 'broken.py'), 'w') as broken:
            broken.write("raise RuntimeError('this game file is broken')\n")
        result = run_script(self.workdir, self.MENU, '1\nbroken.py\n2\n3\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Please Select Option 1 and load valid game file', result.stdout)
        self.assertIn('You have chosen to finish the game thanks for playing', result.stdout)

    def test_load_play_finish_then_game_is_consumed(self):
        answers = '1\ntemplate.py\n2\n' + TEMPLATE_PLAY_INPUT + '2\n3\n'
        result = run_script(self.workdir, self.MENU, answers)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('[Game Loaded]', result.stdout)
        self.assertIn('Have fun creating your stories!', result.stdout)
        # After finishing, the old save must not allow continuing to a "next step".
        self.assertIn('Please Select Option 1 and load valid game file', result.stdout)
        self.assertIn('You have chosen to finish the game thanks for playing', result.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.workdir, 'current_game.ch')))

    def test_stale_save_from_a_previous_run_is_cleared_on_startup(self):
        run_script(self.workdir, 'template.py', '')
        self.assertTrue(os.path.exists(os.path.join(self.workdir, 'current_game.ch')))
        result = run_script(self.workdir, self.MENU, '2\n3\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Please Select Option 1 and load valid game file', result.stdout)

    def test_full_menu_flow_runs_repeatedly(self):
        answers = '1\ntemplate.py\n2\n' + TEMPLATE_PLAY_INPUT + '3\n'
        first = run_script(self.workdir, self.MENU, answers)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.workdir, 'current_game.ch')))
        second = run_script(self.workdir, self.MENU, answers)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.workdir, 'current_game.ch')))


if __name__ == '__main__':
    unittest.main()
