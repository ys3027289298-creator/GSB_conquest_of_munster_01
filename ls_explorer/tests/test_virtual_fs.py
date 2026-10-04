"""Virtual filesystem tests: sync with the real directory tree and
path-escape protection."""
import os
import unittest

from tests.helpers import SandboxCase

import filesystem_utils as fs


class SyncTest(SandboxCase):
    """Bug reproduced: the simulated filesystem drifted out of sync with
    the real directory (stale snapshot, no parent navigation)."""

    def test_listing_matches_real_directory(self):
        vfs = fs.VirtualFileSystem(self.root)
        self.assertEqual({'alpha', 'beta'}, set(vfs.list_dirs()))
        self.assertEqual(set(), set(vfs.list_files()))

    def test_listing_reflects_real_changes(self):
        vfs = fs.VirtualFileSystem(self.root)
        os.mkdir(os.path.join(self.root, 'gamma'))
        with open(os.path.join(self.root, 'new.txt'), 'w') as handle:
            handle.write('x')
        self.assertIn('gamma', vfs.list_dirs())
        self.assertIn('new.txt', vfs.list_files())

    def test_cd_into_child(self):
        vfs = fs.VirtualFileSystem(self.root)
        vfs.cd('alpha')
        self.assertEqual(os.path.realpath(self.alpha),
                         os.path.realpath(vfs.cwd))
        self.assertEqual(['inner'], vfs.list_dirs())
        self.assertEqual(['note.txt'], vfs.list_files())

    def test_cd_dotdot_goes_to_parent(self):
        vfs = fs.VirtualFileSystem(self.root)
        vfs.cd('alpha')
        vfs.cd('..')
        self.assertEqual(os.path.realpath(self.root),
                         os.path.realpath(vfs.cwd))

    def test_cd_absolute_path_inside_root(self):
        vfs = fs.VirtualFileSystem(self.root)
        vfs.cd(self.beta)
        self.assertEqual(os.path.realpath(self.beta),
                        os.path.realpath(vfs.cwd))

    def test_fetch_path_info_still_works(self):
        info = fs.fetch_path_info(self.alpha)
        self.assertEqual([(self.alpha, ['inner'], ['note.txt'])], info)


class PathEscapeTest(SandboxCase):
    """Bug reproduced: nothing stopped the player from wandering outside
    the sandbox root."""

    def test_cd_dotdot_at_root_is_blocked(self):
        vfs = fs.VirtualFileSystem(self.root)
        with self.assertRaises(fs.PathOutOfBoundsError):
            vfs.cd('..')
        self.assertEqual(os.path.realpath(self.root),
                         os.path.realpath(vfs.cwd))

    def test_cd_absolute_path_outside_root_is_blocked(self):
        vfs = fs.VirtualFileSystem(self.root)
        with self.assertRaises(fs.PathOutOfBoundsError):
            vfs.cd('/')
        with self.assertRaises(fs.PathOutOfBoundsError):
            vfs.cd(os.path.expanduser('~'))

    def test_cd_sneaky_relative_escape_is_blocked(self):
        vfs = fs.VirtualFileSystem(self.root)
        vfs.cd('alpha')
        with self.assertRaises(fs.PathOutOfBoundsError):
            vfs.cd(os.path.join('..', '..'))

    def test_cd_missing_directory(self):
        vfs = fs.VirtualFileSystem(self.root)
        with self.assertRaises(fs.NotADirectoryError):
            vfs.cd('nowhere')

    def test_cd_onto_a_file(self):
        vfs = fs.VirtualFileSystem(self.root)
        vfs.cd('alpha')
        with self.assertRaises(fs.NotADirectoryError):
            vfs.cd('note.txt')

    def test_empty_target_rejected(self):
        vfs = fs.VirtualFileSystem(self.root)
        with self.assertRaises(fs.NotADirectoryError):
            vfs.cd('')
        with self.assertRaises(fs.NotADirectoryError):
            vfs.cd(None)


if __name__ == '__main__':
    unittest.main()
