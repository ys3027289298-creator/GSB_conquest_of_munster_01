import os
import pickle
import random
import subprocess
import sys
import time
from os import path

# A game file left over from a previous run must not leak into this session.
if path.exists('current_game.ch'):
    os.remove('current_game.ch')

# menu option for running of game
while True:
    def show_menu():
        # while statement to handle invalid data type entry
        while True:
            try:
                choice = int(input('Welcome to the Conquest of Munster Word Game \n'
                                   'Please Select a number from the following options \n'
                                   '1. Enter Game File to Play \n'
                                   '2. Start Game\n'
                                   '3. Quit \n'
                                   '>>>> '))
                if 0 < choice <= 3:
                    # once user has selected an option, the program user choice is passed to the get choice method
                    get_choice(choice)
                #  if number less than 1 or greater than 3 chosen
                else:  # re-runs choice option
                    print("Please enter valid options only")
            # for handling of string data instead of numeric options
            except ValueError:
                print("Please enter valid options only")
            # input stream closed (e.g. Ctrl+D); exit cleanly instead of crashing
            except EOFError:
                sys.exit(0)

    # handles the users choice
    def get_choice(choice):
        if choice == 1:  # call on program to run default template file
            game_name = input("Please enter file name of the game you wish to play")
            # check if game file exists in directory
            if path.exists(game_name):
                # discard any previous game file before loading the new one
                if path.exists('current_game.ch'):
                    os.remove('current_game.ch')
                # run the game file in its own process so it cannot pollute the menu state
                subprocess.run([sys.executable, game_name])
            else:
                print("That game file does not exist")
        elif choice == 2:  # call on program to request game file name
            story = load_game()
            if story is not None:
                play_story(story)
                # a finished game is consumed so it cannot be continued or replayed
                os.remove('current_game.ch')
            else:
                print("Please Select Option 1 and load valid game file")
        elif choice == 3:  # calls on program to exit as per users request
            print("You have chosen to finish the game thanks for playing")
            exit()

    # Loads the current game file, returning None (and discarding the file) when it is missing or unreadable.
    def load_game():
        if not path.exists('current_game.ch'):
            return None
        try:
            with open('current_game.ch', 'rb') as chapter:
                story = pickle.load(chapter)
        except (OSError, EOFError, pickle.UnpicklingError):
            story = None
        if not isinstance(story, dict):
            os.remove('current_game.ch')
            return None
        return story

    # Game Engine Function from Original Game Engine.py file
    # Function: Slows down text output to output one word at a time, instead of the whole line at once.
    def slow_text(text):
        typing_speed = 100  # words per minute
        for letter in text:
            sys.stdout.write(letter)
            sys.stdout.flush()
            time.sleep(random.random() * 10.0 / typing_speed)
        print('')

    # Function: Slows down text output to output only one line each time before requiring the user to press 'enter'
    def continue_text(lines: list):
        for line in lines:
            slow_text(line)
            # Forces the user to press 'enter' after each line
            get_user_input([""])

    # Function: Takes input from the user. If the user inputs something invalid, it loops, else it returns the input.
    def get_user_input(valid_input: list):
        while True:
            try:
                user_entered = input()
            except EOFError:
                sys.exit(0)

            if user_entered not in valid_input:
                print("Invalid input. Please use one of the following inputs:\n")
                print(valid_input)

            else:
                return user_entered

    # Function: Iterates over the options and allocates a number to each response
    def create_response(options: list):
        for index, option in enumerate(options):
            print(str(index) + ". " + option[0])

        valid_inputs = [str(num) for num in range(len(options))]
        option_index = int(get_user_input(valid_inputs))

        return options[option_index][1]

    # Function: Sets the initial page to 1, keeps turning pages until current page is none.
    def play_story(game: dict):
        current_page = 1

        while current_page is not None:
            page = game.get(current_page, None)

            if page is None:
                break

            continue_text(page.get('Text', []))

            options = page.get('Options', [])
            if len(options) == 0:
                break

            current_page = create_response(options)


    def main():
        show_menu()


    main()
