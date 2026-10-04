'''Covers the simulated filesystem: mirroring the real directory tree,
resyncing after external changes, and path-escape protection.'''
import os

import pytest

import filesystem_utils as f


class TestVirtualFSBasics:
    def test_root_must_be_a_directory(self, tmp_path):
        with pytest.raises(ValueError):
            f.VirtualFS(str(tmp_path / 'missing'))
        not_a_dir = tmp_path / 'file.txt'
        not_a_dir.write_text('x')
        with pytest.raises(ValueError):
            f.VirtualFS(str(not_a_dir))

    def test_listing_matches_real_directory(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        dirs, files = vfs.listdir()
        assert dirs == ['castle', 'forest']
        assert files == ['README.txt']

    def test_starts_at_root(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        assert vfs.cwd == vfs.root

    def test_listdir_of_subdirectory(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        dirs, files = vfs.listdir('castle')
        assert dirs == ['tower']
        assert files == ['note.txt']


class TestSync:
    def test_sync_picks_up_new_files(self, fs_tree):
        # Reproduces: simulated filesystem drifting out of sync with the
        # real directory it mirrors.
        vfs = f.VirtualFS(str(fs_tree))
        vfs.listdir()
        (fs_tree / 'spawned.txt').write_text('new')
        vfs.sync()
        _, files = vfs.listdir()
        assert 'spawned.txt' in files

    def test_sync_picks_up_new_directories(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        (fs_tree / 'dungeon').mkdir()
        vfs.sync()
        dirs, _ = vfs.listdir()
        assert 'dungeon' in dirs

    def test_sync_picks_up_removed_entries(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        (fs_tree / 'README.txt').unlink()
        vfs.sync()
        _, files = vfs.listdir()
        assert 'README.txt' not in files

    def test_sync_resets_cwd_if_it_vanished(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        vfs.cd('forest')
        (fs_tree / 'forest').rmdir()
        vfs.sync()
        assert vfs.cwd == vfs.root


class TestMovementAndPathValidation:
    def test_cd_into_subdirectory(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        expected = os.path.join(vfs.root, 'castle')
        assert vfs.cd('castle') == expected
        assert vfs.cwd == expected

    def test_cd_dotdot_returns_to_parent(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        vfs.cd('castle')
        assert vfs.cd('..') == vfs.root

    def test_cd_dotdot_cannot_escape_root(self, fs_tree):
        # Reproduces: path escape beyond the simulated root.
        vfs = f.VirtualFS(str(fs_tree))
        assert vfs.cd('..') is None
        assert vfs.cwd == vfs.root

    def test_cd_traversal_sequence_cannot_escape(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        vfs.cd('castle')
        assert vfs.cd('../../..') is None
        assert vfs.cwd.startswith(vfs.root)

    def test_cd_absolute_path_outside_root_rejected(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        assert vfs.cd('/') is None
        assert vfs.cd('/etc') is None
        assert vfs.resolve('/etc') is None

    def test_cd_absolute_path_inside_root_allowed(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        target = os.path.join(vfs.root, 'castle', 'tower')
        assert vfs.cd(target) == target

    def test_cd_into_file_fails(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        assert vfs.cd('README.txt') is None
        assert vfs.cwd == vfs.root

    def test_cd_missing_directory_fails(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        assert vfs.cd('nowhere') is None

    def test_resolve_rejects_bad_input(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        assert vfs.resolve('') is None
        assert vfs.resolve(None) is None
        assert vfs.resolve('nowhere') is None

    def test_is_dir_and_is_file(self, fs_tree):
        vfs = f.VirtualFS(str(fs_tree))
        assert vfs.is_dir('castle')
        assert not vfs.is_dir('README.txt')
        assert vfs.is_file('README.txt')
        assert not vfs.is_file('castle')


class TestLegacyFetchPathInfo:
    def test_fetch_path_info_format(self, fs_tree):
        info = f.fetch_path_info(str(fs_tree))
        path, dirs, files = info[0]
        assert path == str(fs_tree)
        assert 'castle' in dirs
        assert 'README.txt' in files
