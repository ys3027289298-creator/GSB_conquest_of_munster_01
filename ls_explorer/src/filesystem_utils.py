# Started: 2/20/2016
# (Worked on VERY intermittently)
# These are functions to return information about the directory tree and its
# files. Formatting and narrative content are found elsewhere.

import os
import logging
import datetime

logger = logging.getLogger('explorer.filesystem')


def test():
    logger.info('This is the test function')


def _list_directory(path):
    '''List one real directory, returning (dirs, files), both name-sorted.'''
    dirs = []
    files = []
    for name in os.listdir(path):
        full_path = os.path.join(path, name)
        if os.path.isdir(full_path):
            dirs.append(name)
        elif os.path.isfile(full_path):
            files.append(name)
    return sorted(dirs), sorted(files)


def fetch_path_info(path=None):
    '''Get the file and directory info for a given path'''
    if path is None:
        path = os.getcwd()
    logger.info('Collecting file & directory info for {}'.format(path))
    dirs, files = _list_directory(path)
    logger.info('{} directories found'.format(len(dirs)))
    logger.info('{} files found'.format(len(files)))
    return [(path, dirs, files)]  # copying os.walk format for now


class VirtualFS(object):
    '''A simulated filesystem rooted at a real directory.

    Directory listings are cached so the game world does not change while
    the player is looking at it; call sync() to re-read the real
    directory tree after files or directories have changed underneath the
    simulation. All movement is confined to the root: parent traversal
    ('..') and absolute paths that would lead outside the root are
    rejected.
    '''

    def __init__(self, root):
        if not root or not os.path.isdir(root):
            raise ValueError('Not a directory: {!r}'.format(root))
        self.root = os.path.realpath(root)
        self._prefix = self.root if self.root.endswith(os.sep) else self.root + os.sep
        self._cache = {}
        self.cwd = self.root
        self.sync()

    def sync(self):
        '''Re-read the entire rooted tree from disk, refreshing the cache.

        If the simulated current directory has vanished from the real
        filesystem, the player is brought back to the root.
        '''
        self._cache = {}
        for dirpath, dirnames, filenames in os.walk(self.root):
            real_path = os.path.realpath(dirpath)
            self._cache[real_path] = (sorted(dirnames), sorted(filenames))
        if self.cwd not in self._cache:
            self.cwd = self.root
        return self

    def _entries(self, path):
        if path not in self._cache:
            self._cache[path] = _list_directory(path)
        return self._cache[path]

    def _inside_root(self, path):
        return path == self.root or path.startswith(self._prefix)

    def resolve(self, target):
        '''Resolve target to an absolute, existing directory inside the
        root. Returns None for missing, non-directory, or escaping paths.
        '''
        if not target or not isinstance(target, str):
            return None
        if os.path.isabs(target):
            candidate = target
        else:
            candidate = os.path.join(self.cwd, target)
        candidate = os.path.realpath(os.path.normpath(candidate))
        if not self._inside_root(candidate):
            logger.info('Refused to resolve {}: outside of root {}'.format(target, self.root))
            return None
        if not os.path.isdir(candidate):
            return None
        return candidate

    def listdir(self, target=None):
        '''Return (dirs, files) for target (default: the current directory),
        or None if target cannot be resolved.'''
        path = self.cwd if target is None else self.resolve(target)
        if path is None:
            return None
        return self._entries(path)

    def is_dir(self, name):
        return self.resolve(name) is not None

    def is_file(self, name):
        _, files = self._entries(self.cwd)
        return name in files

    def cd(self, target):
        '''Move the simulated current directory.

        Returns the new current directory, or None if the move is not
        allowed (target missing, a file, or outside the root).
        '''
        destination = self.resolve(target)
        if destination is None:
            logger.info('Rejected move from {} to {!r}'.format(self.cwd, target))
            return None
        self.cwd = destination
        return self.cwd


if __name__ == "__main__":
    fetch_path_info()
