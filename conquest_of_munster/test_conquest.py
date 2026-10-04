import io
import os
import pickle
import runpy
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

import engine
import menu_engine

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(REPO_DIR, 'template.py')
MENU_TEMPLATE = os.path.join(REPO_DIR, 'menu_template.py')
DRAGONSLAYER = os.path.join(REPO_DIR, 'dragonslayer.py')
ENGINE = os.path.join(REPO_DIR, 'engine.py')
CHAPTER_FILE = 'current_game.ch'

# Enter presses for each text line, followed by the option number, walking
# pages 1 -> 2 -> 3 -> 4 -> 5 of the template story.
TEMPLATE_WALKTHROUGH = ['', '', '0', '', '', '', '0', '', '0', '', '0', '', '']

# Pages 1 -> 2 -> 8: walk into the windy cave and die.
DRAGON_DEATH_WALKTHROUGH = ['', '', '', '0', '', '', '1', '', '', '']


class ScriptedInput:
    """Mimics a piped input stream: prints prompts, replays answers, then EOFs."""

    def __init__(self, answers):
        self._answers = list(answers)

    def __call__(self, prompt=''):
        print(prompt, end='')
        if not self._answers:
            raise EOFError()
        answer = self._answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer


def load_story_from(game_file):
    runpy.run_path(game_file)
    with open(CHAPTER_FILE, 'rb') as chapter:
        return pickle.load(chapter)


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._old_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def run_engine(self, game, inputs):
        output = io.StringIO()
        with mock.patch('builtins.input', ScriptedInput(inputs)), \
                mock.patch('time.sleep', lambda *args: None), \
                redirect_stdout(output):
            engine.play_story(game)
        return output.getvalue()

    def run_menu(self, inputs):
        output = io.StringIO()
        with mock.patch('builtins.input', ScriptedInput(inputs)), \
                mock.patch('time.sleep', lambda *args: None), \
                redirect_stdout(output):
            with self.assertRaises(SystemExit):
                menu_engine.show_menu()
        return output.getvalue()


class TemplateParsingTest(TempDirTestCase):
    def test_template_and_menu_template_produce_the_same_story(self):
        template_story = load_story_from(TEMPLATE)
        menu_story = load_story_from(MENU_TEMPLATE)
        self.assertEqual(template_story, menu_story)

    def test_game_files_have_no_missing_fields(self):
        for game_file in (TEMPLATE, MENU_TEMPLATE, DRAGONSLAYER):
            with self.subTest(game_file=game_file):
                story = load_story_from(game_file)
                self.assertIn(1, story)
                for page_number, page in story.items():
                    self.assertIsInstance(page.get('Text'), list)
                    self.assertIsInstance(page.get('Options'), list)
                    for line in page['Text']:
                        self.assertIsInstance(line, str)
                    for option in page['Options']:
                        self.assertEqual(len(option), 2)
                        self.assertIsInstance(option[0], str)
                        self.assertIn(option[1], story)

    def test_dragonslayer_death_pages_are_terminal(self):
        story = load_story_from(DRAGONSLAYER)
        for page in story.values():
            if any('THE END' in line for line in page['Text']):
                self.assertEqual(page['Options'], [])


class EngineTest(TempDirTestCase):
    def test_empty_chapters_and_missing_fields_do_not_crash(self):
        self.run_engine({}, [])
        self.run_engine({1: {}}, [])
        self.run_engine({1: {'Options': []}}, [])
        self.run_engine('not a dict', [])
        self.run_engine({1: {'Text': ['hello']}}, [EOFError()])
        self.run_engine({1: {'Text': [], 'Options': [('go', 99)]}}, ['0'])

    def test_looping_chapter_ends_when_input_stream_closes(self):
        game = {1: {'Text': ['loop'], 'Options': [('again', 1)]}}
        output = self.run_engine(game, ['', '0', '', '0', EOFError()])
        self.assertIn('loop', output)

    def test_full_template_playthrough(self):
        story = load_story_from(TEMPLATE)
        output = self.run_engine(story, TEMPLATE_WALKTHROUGH)
        self.assertIn('Have fun creating your stories!', output)

    def test_engine_main_without_chapter_file_fails_cleanly(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as context:
            runpy.run_path(ENGINE, run_name='__main__')
        self.assertEqual(context.exception.code, 1)
        self.assertNotIn('Traceback', output.getvalue())

    def test_engine_main_with_empty_chapter_file_fails_cleanly(self):
        with open(CHAPTER_FILE, 'wb') as chapter:
            chapter.write(b'')
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as context:
            runpy.run_path(ENGINE, run_name='__main__')
        self.assertEqual(context.exception.code, 1)
        self.assertNotIn('Traceback', output.getvalue())


class MenuStateMachineTest(TempDirTestCase):
    def test_quit(self):
        output = self.run_menu(['3'])
        self.assertIn('You have chosen to finish the game thanks for playing', output)

    def test_out_of_range_choice_is_not_swallowed(self):
        output = self.run_menu(['5', '3'])
        self.assertEqual(output.count('Welcome to the Conquest of Munster Word Game'), 2)
        self.assertIn('You have chosen to finish the game thanks for playing', output)

    def test_non_numeric_choice_recovers(self):
        output = self.run_menu(['abc', '3'])
        self.assertIn('Please enter valid options only', output)
        self.assertIn('You have chosen to finish the game thanks for playing', output)

    def test_start_without_loaded_game(self):
        output = self.run_menu(['2', '3'])
        self.assertIn('Please Select Option 1 and load valid game file', output)

    def test_missing_game_file(self):
        output = self.run_menu(['1', 'does_not_exist.py', '3'])
        self.assertIn('That game file does not exist', output)
        self.assertIn('You have chosen to finish the game thanks for playing', output)

    def test_invalid_game_file_does_not_crash_menu(self):
        with open('broken.py', 'w') as game_file:
            game_file.write('this is not a valid game file !!!\n')
        output = self.run_menu(['1', 'broken.py', '3'])
        self.assertIn('That game file could not be loaded', output)
        self.assertFalse(os.path.exists(CHAPTER_FILE))
        self.assertIn('You have chosen to finish the game thanks for playing', output)

    def test_game_file_cannot_pollute_menu_state(self):
        with open('hostile.py', 'w') as game_file:
            game_file.write(
                "show_menu = None\n"
                "get_choice = None\n"
                "import pickle\n"
                "story = {1: {'Text': ['hello'], 'Options': []}}\n"
                "with open('current_game.ch', 'wb') as chapter:\n"
                "    pickle.dump(story, chapter)\n"
            )
        output = self.run_menu(['1', 'hostile.py', '2', '', '3'])
        self.assertIn('hello', output)
        self.assertIn('You have chosen to finish the game thanks for playing', output)

    def test_finished_run_leaves_no_stale_save(self):
        inputs = ['1', TEMPLATE, '2'] + TEMPLATE_WALKTHROUGH + ['2', '3']
        output = self.run_menu(inputs)
        self.assertIn('Have fun creating your stories!', output)
        self.assertFalse(os.path.exists(CHAPTER_FILE))
        self.assertIn('Please Select Option 1 and load valid game file', output)

    def test_dragonslayer_failure_cannot_continue(self):
        inputs = ['1', DRAGONSLAYER, '2'] + DRAGON_DEATH_WALKTHROUGH + ['2', '3']
        output = self.run_menu(inputs)
        self.assertIn('THE END', output)
        self.assertFalse(os.path.exists(CHAPTER_FILE))
        self.assertIn('Please Select Option 1 and load valid game file', output)

    def test_repeated_runs(self):
        inputs = ['1', TEMPLATE, '2'] + TEMPLATE_WALKTHROUGH \
            + ['1', TEMPLATE, '2'] + TEMPLATE_WALKTHROUGH + ['3']
        output = self.run_menu(inputs)
        self.assertEqual(output.count('Have fun creating your stories!'), 2)
        self.assertFalse(os.path.exists(CHAPTER_FILE))


if __name__ == '__main__':
    unittest.main()
