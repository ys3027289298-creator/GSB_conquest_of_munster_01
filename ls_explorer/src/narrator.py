# Begun: 2017-02-07 
from __future__ import print_function
import json
import string
import os, sys
import logging
import utils as u
import commands as c
import filesystem_utils as f

logger = logging.getLogger('explorer.narrator')

# one-shot story beats keyed by event id; 'enter:<path>' events are
# generated on the fly when the player first enters a directory
DEFAULT_EVENTS = {
    'first_look': 'You take a moment to orient yourself.',
}


class Story(object):
    '''Tracks one-shot story events so each beat is narrated only once,
    no matter how many times the triggering command is repeated.'''

    def __init__(self, events=None, triggered=None):
        self.events = dict(events or {})
        self.triggered = list(triggered or [])

    def trigger(self, event_id, text=None):
        '''Fire an event once: returns its text the first time it is
        triggered, and None on every subsequent trigger.'''
        if event_id in self.triggered:
            return None
        if text is None:
            text = self.events.get(event_id)
        if text is None:
            return None
        self.triggered.append(event_id)
        return text

    def to_dict(self):
        return {'triggered': list(self.triggered)}

    @classmethod
    def from_dict(cls, data, events=None):
        return cls(events=events, triggered=(data or {}).get('triggered', []))


class GameState(object):
    '''Bundles the simulated filesystem and the story progress, and
    handles saving/loading the game, including the current location.'''

    def __init__(self, root, story=None):
        self.fs = f.VirtualFS(root)
        self.story = story if story is not None else Story(events=DEFAULT_EVENTS)

    def save(self, save_path):
        '''Write the current game state (location included) as JSON.'''
        data = {
            'root': self.fs.root,
            'cwd': self.fs.cwd,
            'story': self.story.to_dict(),
        }
        with open(save_path, 'w') as save_file:
            json.dump(data, save_file, indent=2)
        logger.info('Game saved to {}'.format(save_path))
        return save_path

    @classmethod
    def load(cls, save_path):
        '''Restore a saved game, putting the player back where they were.

        If the saved location no longer exists inside the root, the
        player is returned to the root instead of being lost.
        '''
        with open(save_path) as save_file:
            data = json.load(save_file)
        state = cls(data['root'])
        saved_cwd = data.get('cwd')
        restored_cwd = state.fs.resolve(saved_cwd) if saved_cwd else None
        state.fs.cwd = restored_cwd if restored_cwd else state.fs.root
        state.story = Story.from_dict(data.get('story'), events=DEFAULT_EVENTS)
        logger.info('Game loaded from {}'.format(save_path))
        return state


def save_game(state, save_path):
    '''Save the game state (including current location) to a file.'''
    return state.save(save_path)


def load_game(save_path):
    '''Load a previously saved game state from a file.'''
    return GameState.load(save_path)


def narrate(input_func=input, state=None):
    ''' Simple function to provide a user prompt, accept input, and pass it
    along to the functions that recognize and fulfill commands '''
    logger.info('Beginning narrate function')
    if state is None:
        state = GameState(os.getcwd())
    print("Welcome! Type '{0}quit{1}' at any time to stop the program. Type '{0}help{1}' to see your options.".format(u.colors['red'], u.colors['default']))
    while True: 
        try:
            user_input = input_func('{0}> {1}'.format(u.colors['black'], u.colors['default']))
        except EOFError:
            logger.info('Input stream closed; ending narration')
            break
        if not user_input or not user_input.strip():
            logger.info('User submitted an empty command; ignoring it')
            continue
        command = c.extract_commands(user_input)
        if command is None:
            logger.info('User has specified no command words')
            continue
        c.execute_command(command, user_input, state=state)

def validate_path(current_path, input_text):
    ''' Returns any valid absolute path via user input, or None.

    Relative input is resolved against current_path and normalized, so
    '..' segments can never take the result above the filesystem root.
    '''
    if not input_text or not isinstance(input_text, str):
        return None
    candidate = input_text.strip()
    if not candidate:
        return None
    if not os.path.isabs(candidate):
        candidate = os.path.join(current_path, candidate)
    candidate = os.path.normpath(candidate)
    if os.path.exists(candidate):
        return candidate
    return None
    
def look(path=None, rest_of_text=None):
    ''' Prints out the files and directories '''
    logger.info('Now preparing to narrate for {}'.format(path or os.getcwd()))
    return c.execute_look(path=path, rest_of_text=rest_of_text)

def move_path(path=None, rest_of_text=None):
    ''' Changes the scope of focus to a different filepath '''
    logger.info('Now running move_path function')
    if path is None:
        path = os.getcwd()
    available_dirs = [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]
    # check to see if rest_of_text contains a file or folder
    # if file:
    # if garbage (nothing recognized):
    # if no text:
    if not rest_of_text or not rest_of_text.strip():
        logger.info('User wants to move, but did not supply any further input')
        user_input = input('Where do you want to move? (Type \'look\' to see available options.) ')
        if user_input.lower() == 'look':
            logger.info('User chose to look at current directory: {}'.format(path))
            look(path)
    # if directory:
    #if 
    return None
    

if __name__ == '__main__':
    narrate()
