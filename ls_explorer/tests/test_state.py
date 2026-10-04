'''Covers story-event deduplication and save/load state restoration.'''
import json
import os

import pytest

import narrator as n


class TestStoryEvents:
    def test_event_fires_exactly_once(self):
        # Reproduces: repeated commands re-triggering story beats.
        story = n.Story(events={'looked': 'You look around.'})
        assert story.trigger('looked') == 'You look around.'
        assert story.trigger('looked') is None
        assert story.trigger('looked') is None

    def test_unknown_event_returns_none(self):
        assert n.Story().trigger('nope') is None

    def test_inline_event_text(self):
        story = n.Story()
        assert story.trigger('enter:hall', text='You enter the hall.') == 'You enter the hall.'
        assert story.trigger('enter:hall', text='You enter the hall.') is None

    def test_triggered_events_survive_save_load(self, fs_tree, tmp_path):
        state = n.GameState(str(fs_tree))
        state.story.trigger('first_look')
        save_file = str(tmp_path / 'save.json')
        state.save(save_file)
        restored = n.GameState.load(save_file)
        assert restored.story.trigger('first_look') is None


class TestSaveLoad:
    def test_current_location_restored_after_load(self, fs_tree, tmp_path):
        # Reproduces: loading a save lost the player's current location.
        state = n.GameState(str(fs_tree))
        state.fs.cd('castle')
        state.fs.cd('tower')
        save_file = str(tmp_path / 'save.json')
        state.save(save_file)
        restored = n.GameState.load(save_file)
        assert restored.fs.cwd == state.fs.cwd
        assert restored.fs.cwd.endswith(os.path.join('castle', 'tower'))

    def test_save_file_contains_root_cwd_and_story(self, fs_tree, tmp_path):
        state = n.GameState(str(fs_tree))
        state.fs.cd('forest')
        save_file = str(tmp_path / 'save.json')
        state.save(save_file)
        with open(save_file) as fh:
            data = json.load(fh)
        assert data['root'] == state.fs.root
        assert data['cwd'] == state.fs.cwd
        assert 'story' in data

    def test_load_with_vanished_directory_falls_back_to_root(self, fs_tree, tmp_path):
        state = n.GameState(str(fs_tree))
        state.fs.cd('forest')
        save_file = str(tmp_path / 'save.json')
        state.save(save_file)
        (fs_tree / 'forest').rmdir()
        restored = n.GameState.load(save_file)
        assert restored.fs.cwd == restored.fs.root

    def test_module_level_save_and_load_helpers(self, fs_tree, tmp_path):
        state = n.GameState(str(fs_tree))
        state.fs.cd('castle')
        save_file = str(tmp_path / 'save.json')
        n.save_game(state, save_file)
        restored = n.load_game(save_file)
        assert restored.fs.cwd == state.fs.cwd

    def test_load_missing_save_file_raises(self, tmp_path):
        with pytest.raises((IOError, OSError)):
            n.load_game(str(tmp_path / 'no_such_save.json'))

