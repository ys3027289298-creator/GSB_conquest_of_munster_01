"""Save / load (state restoration) tests.

Bug reproduced: loading a save lost the player's current location and
dumped them back at the starting directory.
"""
import json
import os
import unittest

from tests.helpers import SandboxCase, run_silently

import commands
import narrator


class SaveLoadTest(SandboxCase):
    def setUp(self):
        super().setUp()
        self.save_file = os.path.join(self.root, 'save.json')

    def test_round_trip_restores_location(self):
        state = narrator.GameState(self.root)
        state.vfs.cd('alpha')
        state.vfs.cd('inner')
        state.save(self.save_file)

        fresh = narrator.GameState(self.root)
        self.assertNotEqual(state.vfs.cwd, fresh.vfs.cwd)
        fresh.load(self.save_file)
        self.assertEqual(os.path.realpath(state.vfs.cwd),
                         os.path.realpath(fresh.vfs.cwd))

    def test_round_trip_restores_story_progress(self):
        state = narrator.GameState(self.root)
        run_silently(commands.execute_command, 'go', state, 'go alpha',
                     'alpha')
        state.save(self.save_file)

        fresh = narrator.GameState(self.root)
        fresh.load(self.save_file)
        self.assertEqual(state.seen, fresh.seen)
        # re-entering the same place must stay silent after a reload
        _, output = run_silently(commands.execute_command, 'go', fresh,
                                 'go ..', '..')
        _, output = run_silently(commands.execute_command, 'go', fresh,
                                 'go alpha', 'alpha')
        self.assertNotIn(commands.STORY_FIRST_VISIT.split('{')[0], output)

    def test_save_file_is_valid_json(self):
        state = narrator.GameState(self.root)
        state.vfs.cd('beta')
        state.save(self.save_file)
        with open(self.save_file) as handle:
            data = json.load(handle)
        self.assertEqual(os.path.realpath(self.beta),
                         os.path.realpath(data['cwd']))
        self.assertEqual(os.path.realpath(self.root),
                         os.path.realpath(data['root']))

    def test_load_missing_file_raises(self):
        state = narrator.GameState(self.root)
        with self.assertRaises(FileNotFoundError):
            state.load(os.path.join(self.root, 'nope.json'))

    def test_load_corrupt_file_raises(self):
        with open(self.save_file, 'w') as handle:
            handle.write('{ not json')
        state = narrator.GameState(self.root)
        with self.assertRaises(ValueError):
            state.load(self.save_file)

    def test_load_rejects_save_from_other_root(self):
        state = narrator.GameState(self.root)
        state.save(self.save_file)
        other = narrator.GameState(self.alpha)
        with self.assertRaises(ValueError):
            other.load(self.save_file)

    def test_load_with_vanished_directory_falls_back_to_root(self):
        state = narrator.GameState(self.root)
        state.vfs.cd('beta')
        state.save(self.save_file)
        os.rmdir(self.beta)
        fresh = narrator.GameState(self.root)
        fresh.load(self.save_file)
        self.assertEqual(os.path.realpath(self.root),
                         os.path.realpath(fresh.vfs.cwd))

    def test_execute_save_and_load_commands(self):
        state = narrator.GameState(self.root)
        state.save_path = self.save_file
        run_silently(commands.execute_command, 'go', state, 'go alpha',
                     'alpha')
        run_silently(commands.execute_command, 'save', state, 'save', None)

        fresh = narrator.GameState(self.root)
        fresh.save_path = self.save_file
        run_silently(commands.execute_command, 'load', fresh, 'load', None)
        self.assertEqual(os.path.realpath(state.vfs.cwd),
                         os.path.realpath(fresh.vfs.cwd))


if __name__ == '__main__':
    unittest.main()
