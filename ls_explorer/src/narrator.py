# Begun: 2017-02-07
from __future__ import print_function
import json
import os
import logging

import utils as u
import commands as c
import filesystem_utils as fs

logger = logging.getLogger('explorer.narrator')

DEFAULT_SAVE_PATH = os.path.expanduser('~/.ls_explorer_save.json')


class GameState(object):
    ''' Everything the game needs to remember between commands, and
    between sessions: the simulated filesystem position and the set of
    story events that have already fired. '''

    def __init__(self, root=None, save_path=None):
        self.vfs = fs.VirtualFileSystem(root or os.getcwd())
        self.seen = set()
        self.save_path = save_path or DEFAULT_SAVE_PATH

    def save(self, path=None):
        path = path or self.save_path
        data = {
            'root': self.vfs.root,
            'cwd': self.vfs.cwd,
            'seen': sorted(self.seen),
        }
        with open(path, 'w') as handle:
            json.dump(data, handle, indent=2)
        logger.info('Game saved to {}'.format(path))
        return path

    def load(self, path=None):
        path = path or self.save_path
        if not os.path.exists(path):
            raise FileNotFoundError('No saved game at {}'.format(path))
        try:
            with open(path) as handle:
                data = json.load(handle)
        except ValueError as exc:
            raise ValueError('Save file {} is corrupt: {}'.format(path, exc))
        if os.path.realpath(data.get('root', '')) != self.vfs.root:
            raise ValueError(
                'Save file {} belongs to a different area'.format(path))
        self.vfs.restore(data)
        self.seen = set(data.get('seen', []))
        logger.info('Game loaded from {} (at {})'.format(path, self.vfs.cwd))


def narrate(state=None):
    ''' Simple function to provide a user prompt, accept input, and pass it
    along to the functions that recognize and fulfill commands '''
    if state is None:
        state = GameState()
    logger.info('Beginning narrate function')
    print("Welcome! Type '{0}quit{1}' at any time to stop the program. Type '{0}help{1}' to see your options.".format(u.colors['red'], u.colors['default']))
    while True:
        user_input = input('{0}> {1}'.format(u.colors['black'], u.colors['default']))
        parsed = c.parse(user_input)
        if parsed is None:
            logger.info('User has specified no command words')
            continue
        c.execute_command(parsed.action, state, parsed.raw, parsed.target)


if __name__ == '__main__':
    narrate()
