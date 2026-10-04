# Started: 2/20/2016
# (Worked on VERY intermittently)
# These are functions to return information about the directory tree and its files. Formatting and narrative content are found elsewhere.

import os
import logging

logger = logging.getLogger('explorer.filesystem')


class PathOutOfBoundsError(Exception):
    ''' Raised when a path would leave the sandbox root. '''


class NotADirectoryError(Exception):
    ''' Raised when a movement target is missing or is not a directory. '''


def _list(path, want_dirs):
    try:
        names = os.listdir(path)
    except OSError:
        return []
    result = []
    for name in names:
        full = os.path.join(path, name)
        if os.path.isdir(full) == want_dirs:
            result.append(name)
    return sorted(result)


class VirtualFileSystem(object):
    ''' A simulated filesystem sandboxed to a root directory.

    The simulation reads the real directory tree on every query, so the
    simulated view can never drift out of sync with the real one, and
    every movement is validated so the player cannot escape the root.
    '''

    def __init__(self, root):
        real_root = os.path.realpath(root)
        if not os.path.isdir(real_root):
            raise NotADirectoryError(
                'Sandbox root is not a directory: {}'.format(root))
        self.root = real_root
        self.cwd = real_root

    def list_dirs(self, path=None):
        return _list(path or self.cwd, want_dirs=True)

    def list_files(self, path=None):
        return _list(path or self.cwd, want_dirs=False)

    def resolve(self, target):
        ''' Resolve a user-supplied target to an absolute path inside the
        sandbox; raises PathOutOfBoundsError if it escapes the root. '''
        if target is None:
            raise NotADirectoryError('No target given')
        target = target.strip()
        if not target:
            raise NotADirectoryError('No target given')
        if not os.path.isabs(target):
            target = os.path.join(self.cwd, target)
        real = os.path.realpath(target)
        if real != self.root and not real.startswith(self.root + os.sep):
            raise PathOutOfBoundsError(
                "'{}' lies outside the explorable area".format(target))
        return real

    def cd(self, target):
        ''' Move the simulated working directory; returns the new cwd. '''
        real = self.resolve(target)
        if not os.path.isdir(real):
            raise NotADirectoryError(
                "'{}' is not a directory".format(target))
        self.cwd = real
        logger.info('Moved to {}'.format(real))
        return real

    def state_dict(self):
        return {'root': self.root, 'cwd': self.cwd}

    def restore(self, data):
        ''' Restore cwd from saved state; falls back to the sandbox root
        if the saved location no longer exists. '''
        saved_cwd = data.get('cwd')
        if saved_cwd:
            try:
                self.cd(saved_cwd)
                return
            except (PathOutOfBoundsError, NotADirectoryError):
                logger.warning('Saved location {} is gone; returning to '
                               'the starting directory'.format(saved_cwd))
        self.cwd = self.root


def test():
    logger.info('This is the test function')


def fetch_path_info(path=None):
    '''Get the file and directory info for a given path'''
    path = path or os.getcwd()
    logger.info('Collecting file & directory info for {}'.format(path))
    dirs = _list(path, want_dirs=True)
    logger.info('{} directories found'.format(len(dirs)))
    files = _list(path, want_dirs=False)
    logger.info('{} files found'.format(len(files)))
    return [(path, dirs, files)] # copying os.walk format for now


if __name__ == "__main__":
    fetch_path_info()
