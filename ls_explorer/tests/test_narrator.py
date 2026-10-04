'''Covers the narrate loop: abnormal input handling, path validation,
story-event deduplication during play, and save/load round trips.'''
import os

import pytest

import narrator as n


def run_session(inputs, fs_tree):
    '''Drive narrate() with scripted input; EOF ends the session.'''
    state = n.GameState(str(fs_tree))
    scripted = iter(inputs)

    def fake_input(prompt=''):
        try:
            return next(scripted)
        except StopIteration:
            raise EOFError

    n.narrate(input_func=fake_input, state=state)
    return state


class TestAbnormalInput:
    def test_empty_input_does_not_crash(self, fs_tree, capsys):
        # Reproduces: pressing enter on an empty prompt crashed the game.
        run_session(['', '   ', '\t\n', 'look'], fs_tree)
        assert 'You see some files:' in capsys.readouterr().out

    def test_garbage_input_does_not_crash(self, fs_tree):
        run_session(['asdfgh', '!!!', '12345', 'go go go'], fs_tree)

    def test_eof_ends_session_cleanly(self, fs_tree):
        run_session([], fs_tree)

    def test_case_and_whitespace_insensitive_commands(self, fs_tree, capsys):
        run_session(['   LoOk   ', '  GO   castle  '], fs_tree)
        out = capsys.readouterr().out
        assert 'You see some files:' in out

    def test_quit_raises_system_exit(self, fs_tree):
        with pytest.raises(SystemExit):
            run_session(['quit'], fs_tree)


class TestMovement:
    def test_go_changes_current_directory(self, fs_tree):
        state = run_session(['go castle'], fs_tree)
        assert state.fs.cwd == os.path.join(state.fs.root, 'castle')

    def test_go_with_case_insensitive_directory_name(self, fs_tree):
        state = run_session(['go CASTLE'], fs_tree)
        assert state.fs.cwd.endswith('castle')

    def test_go_beyond_root_is_rejected(self, fs_tree, capsys):
        # Reproduces: path escape outside the simulated filesystem.
        state = run_session(['go castle', 'go ../../..'], fs_tree)
        assert state.fs.cwd == os.path.join(state.fs.root, 'castle')
        assert 'You cannot go that way.' in capsys.readouterr().out

    def test_go_dotdot_at_root_is_rejected(self, fs_tree, capsys):
        state = run_session(['go ..'], fs_tree)
        assert state.fs.cwd == state.fs.root
        assert 'You cannot go that way.' in capsys.readouterr().out

    def test_go_into_file_is_rejected(self, fs_tree, capsys):
        state = run_session(['go README.txt'], fs_tree)
        assert state.fs.cwd == state.fs.root
        assert 'You cannot go that way.' in capsys.readouterr().out

    def test_go_to_missing_place_is_rejected(self, fs_tree, capsys):
        state = run_session(['go nowhere'], fs_tree)
        assert 'You cannot go that way.' in capsys.readouterr().out


class TestStoryDuringPlay:
    def test_directory_event_fires_only_once(self, fs_tree, capsys):
        # Reproduces: re-entering a directory re-triggered its story beat.
        run_session(['go forest', 'go ..', 'go forest'], fs_tree)
        out = capsys.readouterr().out
        assert out.count('for the first time') == 1

    def test_distinct_directories_each_get_one_event(self, fs_tree, capsys):
        run_session(['go forest', 'go ..', 'go castle'], fs_tree)
        out = capsys.readouterr().out
        assert out.count('for the first time') == 2

    def test_first_look_event_fires_only_once(self, fs_tree, capsys):
        run_session(['look', 'look'], fs_tree)
        out = capsys.readouterr().out
        assert out.count('You take a moment to orient yourself.') == 1


class TestValidatePath:
    def test_valid_relative_subdirectory(self, fs_tree):
        result = n.validate_path(str(fs_tree), 'castle')
        assert result == os.path.join(str(fs_tree), 'castle')

    def test_dotdot_resolves_to_parent(self, fs_tree):
        castle = os.path.join(str(fs_tree), 'castle')
        assert n.validate_path(castle, '..') == str(fs_tree)

    def test_absolute_path_accepted(self, fs_tree):
        assert n.validate_path(str(fs_tree), str(fs_tree)) == str(fs_tree)

    def test_nonexistent_path_returns_none(self, fs_tree):
        assert n.validate_path(str(fs_tree), 'nowhere') is None

    def test_cannot_escape_above_filesystem_root(self):
        assert n.validate_path('/', '../../..') == '/'

    def test_empty_input_returns_none(self, fs_tree):
        assert n.validate_path(str(fs_tree), '') is None
        assert n.validate_path(str(fs_tree), '   ') is None
