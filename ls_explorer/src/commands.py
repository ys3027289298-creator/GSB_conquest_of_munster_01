# started: 2017-09-20
from collections import namedtuple
import string
import os
import sys
import logging

import utils as u
import filesystem_utils as fs

logger = logging.getLogger('explorer.narrator')

# all commands and synonyms
commands = {'quit': ['quit','exit','leave','goodbye','bye','q', 'stop'], \
            'look': ['look','examine', 'ls', 'list', 'dir'], \
            'help': ['help','options','menu','h'], \
            'verbose': ['verbose','debug','v'], \
            'go': ['go','enter','cd','move', 'walk', 'n', 's', 'e', 'w'], \
            'where': ['where','pwd'], \
            'inventory': ['inventory', 'i', 'stuff', 'possessions'], \
            'save': ['save', 'persist'], \
            'load': ['load', 'restore', 'resume']}

# narrative (new, not part of the original teaching text)
STORY_FIRST_VISIT = ("Something about this place feels new... you take in "
                     "{name} for the first time.")
# messages for rejected movement
MSG_CANNOT_GO = ("You can't go that way; it lies outside the explorable "
                 "area.")
MSG_NOT_A_PLACE = "That doesn't look like a place you can go."

# flattened list of all command words, plus a synonym -> key inverse map
ALL_COMMAND_WORDS = [word for synonyms in commands.values()
                     for word in synonyms]
INVERSE_COMMANDS = {word: canonical
                    for canonical, synonyms in commands.items()
                    for word in synonyms}

ParseResult = namedtuple('ParseResult', ['action', 'target', 'raw'])


def _strip_punctuation(word):
    return word.translate(str.maketrans('', '', string.punctuation))


def parse(raw_user_input):
    ''' Parse raw user input into a ParseResult(action, target, raw).

    Normalization rules:
      * None / non-string input is treated as empty, never crashes;
      * casing is ignored for command words and directory targets;
      * any amount of whitespace collapses to single-token separation;
      * punctuation attached to a command word is stripped, but the raw
        following token is preserved as the target (so "go .." keeps "..");
      * several commands at once are resolved by prioritize_commands.
    Returns None when no recognized command is present.
    '''
    if raw_user_input is None:
        return None
    if not isinstance(raw_user_input, str):
        raw_user_input = str(raw_user_input)
    raw_tokens = raw_user_input.split()
    recognized = []  # list of (canonical, target-token or None)
    for index, raw_token in enumerate(raw_tokens):
        clean = _strip_punctuation(raw_token.lower())
        canonical = INVERSE_COMMANDS.get(clean)
        if canonical is None:
            continue
        target = raw_tokens[index + 1] if index + 1 < len(raw_tokens) \
            else None
        recognized.append((canonical, target))
    if not recognized:
        logger.debug('No command words found in: {!r}'.format(raw_user_input))
        return None
    if len(recognized) == 1:
        action, target = recognized[0]
        logger.info("One command found, canonical action '{}'".format(action))
    else:
        action_tuple = tuple(item[0] for item in recognized)
        action = prioritize_commands(action_tuple)
        target = next((item[1] for item in recognized
                       if item[0] == action), None)
    return ParseResult(action=action, target=target, raw=raw_user_input)


def extract_commands(input):
    ''' Processes the raw user input and returns a list of canonical
    command word(s) from a large number of possible synonyms; runs this
    list through a prioritization function to return a single command
    to execute. Returns None for empty, null or unrecognized input. '''
    parsed = parse(input)
    return parsed.action if parsed is not None else None


def prioritize_commands(input):
    ''' Receives a tuple of one or more commands; returns the highest priority
    command as a string '''
    priority_order = ('quit', 'help', 'look', 'go', 'verbose', 'where',
                      'save', 'load', 'inventory')
    priority_index = {cmd: i for i, cmd in enumerate(priority_order)}
    # Manage cases of poor input hygiene:
    if input is None or len(input) == 0:
        logger.error('Received an empty or null list of commands to prioritize')
        return None
    if len(input) == 1:
        return input[0]
    # In the expected case (where the list is 2+ items long):
    command_priorities = tuple(sorted(
        input, key=lambda cmd: priority_index.get(cmd, len(priority_order))))
    logger.info('{} commands found: {}, prioritized in this order: {}'.format(
        len(input), input, command_priorities))
    return command_priorities[0]


def execute_command(action, state=None, raw_user_input=None, target=None):
    ''' Calls the function to execute a specific action. '''
    # when zero arguments are needed:
    if action in ('help', 'quit', 'inventory'):
        correct_function = globals()['execute_{}'.format(action)]
        correct_function()
    # when one argument is needed:
    elif action == 'look':
        execute_look(state)
    elif action == 'where':
        logger.info('User wants an action that is only a placeholder at present')
        print("Haha, this is embarrassing, I haven't coded that yet.")
    elif action == 'go':
        execute_go(state, rest_of_text=raw_user_input, target=target)
    elif action == 'save':
        state.save()
    elif action == 'load':
        state.load()
    else:
        logger.info("We recognize this as a command but don't know what to do about it: {}".format(action))
        print("Sorry! I don't know what to tell you.")


def execute_inventory():
    print('You check your inventory. You have: a stick of gum, a business card, a pair of scissors. I have not programmed any actions you can take with any of these items.')


def execute_quit():
    logger.info('User has chosen to exit')
    print('Goodbye!')
    sys.exit(0)


def execute_help():
    ''' Returns a string that lists all recognized functions and a brief
    description of each. '''
    logger.info('Beginning help function')
    commands = {'look': 'look at current directory', 'go': 'move to another directory', 'quit': 'exit to the command line'}
    first_line = "Feeling lost? Available commands are:"
    command_output = '\n'.join(['{0:5}{1}{2:10}{3}{4}'.format
                                ('', u.colors['red'], x, u.colors['default'],
                                 commands[x]) for x in commands.keys()])
    print('\n'.join([first_line, command_output]))


def execute_look(state):
    ''' Prints out the files and directories of the simulated cwd. '''
    path = state.vfs.cwd
    logger.info('User wants to examine {}'.format(path))
    files = state.vfs.list_files()
    dirs = state.vfs.list_dirs()
    if len(files) < 1:
        print('There are no files here.')
    else:
        print('You see some files: {}'.format(files))
    if len(dirs) < 1:
        print('You can go: back the way you came')
    else:
        print('You can go: {}'.format(dirs))


def _match_directory(state, target):
    ''' Match a target case-insensitively against real directory names,
    falling back to the raw target (covers "..", absolute paths, etc.). '''
    lowered = target.lower()
    for directory in state.vfs.list_dirs():
        if directory.lower() == lowered:
            return directory
    return target


def execute_go(state, rest_of_text=None, target=None):
    ''' Changes the scope of focus to a different filepath. '''
    logger.info('Now running move_path function')
    if target is None or not target.strip():
        logger.info('User wants to move, but did not supply any further input')
        user_input = input('Where do you want to move? (Type \'look\' to see available options.) ')
        if user_input.lower().strip() == 'look':
            logger.info('User chose to look at current directory: {}'.format(
                state.vfs.cwd))
            execute_look(state)
        return
    destination = _match_directory(state, target.strip())
    try:
        new_path = state.vfs.cd(destination)
    except fs.PathOutOfBoundsError:
        logger.info('Movement refused: %s escapes the sandbox', destination)
        print(MSG_CANNOT_GO)
        return
    except fs.NotADirectoryError:
        logger.info('Movement refused: %s is not a directory', destination)
        print(MSG_NOT_A_PLACE)
        return
    event_key = 'enter:' + new_path
    if event_key not in state.seen:
        name = os.path.basename(new_path) or new_path
        print(STORY_FIRST_VISIT.format(name=name))
        state.seen.add(event_key)
