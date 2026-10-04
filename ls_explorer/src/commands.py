# started: 2017-09-20
from __future__ import print_function
import string
import os, sys
import subprocess # to get terminal size
import logging
import utils as u

logger = logging.getLogger('explorer.narrator')

# all commands and synonyms
commands = {'quit': ['quit','exit','leave','goodbye','bye','q', 'stop'], \
            'look': ['look','examine', 'ls', 'list', 'dir'], \
            'help': ['help','options','menu','h'], \
            'verbose': ['verbose','debug','v'], \
            'go': ['go','enter','cd','move', 'walk', 'n', 's', 'e', 'w'], \
            'where': ['where','pwd'], \
            'inventory': ['inventory', 'i', 'stuff', 'possessions']}

def _tokenize(text):
    '''Split raw input into lowercase words with punctuation removed;
    tolerant of any casing and any amount of whitespace.'''
    if not text:
        return []
    punctuation_table = str.maketrans('', '', string.punctuation)
    return text.lower().translate(punctuation_table).split()

def extract_commands(input):
    ''' Processes the raw user input and returns a list of canonical
    command word(s) from a large number of possible synonyms; runs this
    list through a prioritization function to return a single command 
    to execute'''
    # flattened list of all command dictionary values
    all_commands = [x for y in commands.values() for x in y]
    # now identify dict keys for all command words in user input
    word_list = _tokenize(input)
    logger.debug('Processed word list: {}'.format(word_list))
    command_input = [x for x in word_list if x in all_commands]
    if len(command_input) == 0:
        return None
    else:
        # generate inverse dictionary 
        # (Note that efficiency is a non-concern right now)
        inverse_commands = {word: canonical
                            for canonical, words in commands.items()
                            for word in words}
        core_commands = [inverse_commands[i] for i in command_input]
    if len(core_commands) == 1:
        logger.info("One command found: '{}', which is identical or synonymous with '{}'".format(command_input[0], core_commands[0]))
        return core_commands[0]
    else:
        prioritized = prioritize_commands(tuple(core_commands))
        return prioritized

def extract_argument(raw_text):
    '''Return the first whitespace-separated token after the command word,
    preserving characters that paths need (dots, slashes, dashes).'''
    if not raw_text:
        return None
    words = raw_text.split()
    if len(words) < 2:
        return None
    return words[1]

def prioritize_commands(input):
    ''' Receives a tuple of one or more commands; returns the highest priority
    command as a string '''
    priority_order = ('quit','help','look','go','where','verbose','inventory')
    # Manage cases of poor input hygiene:
    if len(input) < 2:
        if len(input) == 1:
            return input[0]
        elif len(input) == 0 or input is None:
            logger.error('Received an empty or null list of commands to prioritize')
            return None
        else: # something extremely weird has happened
            logger.error('We should never see this error. Something unexpected happened while trying to prioritize these commands: {}'.format(input))
            return None
    # In the expected case (where the list is 2+ items long):
    command_priorities = tuple(sorted(input, key=priority_order.index))
    logger.info('{} commands found: {}, prioritized in this order: {}'.format(len(input), input, command_priorities))
    return (command_priorities[0])

def execute_command(action, raw_user_input=None, state=None):
    ''' Calls the function to execute a specific action and performs any 
    other necessary tasks (none yet, but I'm sure I'll think of something) '''
    # when zero arguments are needed: 
    if action in ('help', 'quit', 'inventory', 'verbose'):
        correct_function = globals()['execute_{}'.format(action)]
        correct_function()
    # when one argument is needed: 
    elif action == 'look':
        correct_function = globals()['execute_{}'.format(action)]
        correct_function(rest_of_text=raw_user_input, state=state)
        #print("Feeling lost? Available commands are 'look' (look at current directory) and 'go' (move to another directory). Type 'quit' at any time to stop.")
    elif action == 'where':
        logger.info('User wants an action that is only a placeholder at present')
        print("Haha, this is embarrassing, I haven't coded that yet.")
    elif action == 'go':
        correct_function = globals()['execute_{}'.format(action)]
        correct_function(rest_of_text=raw_user_input, state=state)
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

def execute_verbose():
    ''' Toggles verbose (debug-level) logging on and off. '''
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.setLevel(logging.INFO)
        print('Verbose mode off.')
    else:
        logger.setLevel(logging.DEBUG)
        print('Verbose mode on.')

def format_list(l, column_num=0):
    ''' Takes a list (e.g. of files) and returns a multi-line string with
    the list items nicely padded into columns of empty space. '''
    items = list(l)
    if not items:
        return ''
    spacing = max([len(x) for x in items]) + 4
    if column_num < 1:
        # pick as many columns as the terminal can fit, at least one
        try:
            columns = os.get_terminal_size().columns
        except OSError:
            columns = 80
        column_num = max(1, columns // spacing)
    line_list = []
    i = 0
    while i < len(items):
        single_row = items[i:i+column_num]
        format_string = ''.join(['{:<{fill}}' for x in single_row])
        line_list.append(format_string.format(*single_row, fill=spacing).rstrip())
        i = i + column_num
    return '\n'.join(line_list)

def execute_look(path=None, rest_of_text=None, state=None):
    ''' Prints out the files and directories '''
    if state is not None:
        # re-sync the simulated filesystem with the real directory first,
        # so the player never sees a stale world
        state.fs.sync()
        location = state.fs.cwd
        dirs, files = state.fs.listdir()
    else:
        location = path if path else os.getcwd()
        files = sorted([x for x in os.listdir(location) if os.path.isfile(os.path.join(location, x))])
        dirs = sorted([x for x in os.listdir(location) if os.path.isdir(os.path.join(location, x))])
    logger.info('User wants to examine {}'.format(location))
    if state is not None:
        event_text = state.story.trigger('first_look')
        if event_text:
            print(event_text)
    if len(files) < 1:
        print('There are no files here.')
    else:
        print('You see some files: {}'.format(files))
    if len(dirs) < 1:
        print('You can go: back the way you came')
    else:
        print('You can go: {}'.format(dirs))

def execute_go(path=None, rest_of_text=None, state=None):
    ''' Changes the scope of focus to a different filepath '''
    logger.info('Now running move_path function')
    target = extract_argument(rest_of_text)
    if state is None:
        logger.info('No game state supplied; the move cannot be carried out')
        return None
    fs = state.fs
    # if no text:
    if not target:
        logger.info('User wants to move, but did not supply any further input')
        print("Where do you want to move? (Type 'look' to see available options.)")
        dirs, _ = fs.listdir()
        if len(dirs) < 1:
            print('You can go: back the way you came')
        else:
            print('You can go: {}'.format(dirs))
        return None
    # if directory (also tolerating mismatched letter case):
    destination = fs.resolve(target)
    if destination is None:
        dirs, _ = fs.listdir()
        matches = [d for d in dirs if d.lower() == target.lower()]
        if matches:
            destination = fs.resolve(matches[0])
    # if garbage (nothing recognized) or an escaping path:
    if destination is None:
        logger.info('Rejected move from {} to {!r}'.format(fs.cwd, target))
        print('You cannot go that way.')
        return None
    fs.cd(destination)
    print('You move to {}'.format(fs.cwd))
    # narrate the first visit to each directory (never the root, and
    # never twice for the same place)
    if fs.cwd != fs.root:
        event_text = state.story.trigger(
            'enter:{}'.format(fs.cwd),
            text='You enter {} for the first time.'.format(os.path.basename(fs.cwd)))
        if event_text:
            print(event_text)
    return fs.cwd
