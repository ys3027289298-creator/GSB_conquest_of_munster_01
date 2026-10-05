"""
Module for the different functions for the different dices
- D20: for initiative, attack and skill checks
- D6: for damage
- separate function for rolling the dice and saving the outcome + adding the modifier
- separate functions for the user and enemy

- include natural 20 (double damage) and natural 1?

- function for comparing initiative: user's D20 against enemy's D20
- function for checking if an attack succeeds or fails: D20 against AC (from dict characters) each for user's attack and enemy's attack
- function for checking if a skill check succeeds: user's D20 against DC swimming in the river
"""

from random import randint

def _roll(sides, rng=None):
    if rng is None:
        return randint(1, sides)
    return rng.randint(1, sides)

""" User's dices """
# D6: dice with 6 sides

def user_D6(user, rng=None):
    while True:
        try:
            roll = input("To roll a D6 dice type anything: ")
            if roll:
                user_d6 = _roll(6, rng)
            else:
                raise ValueError("Empty input")   
        except ValueError:
            print("You did not type anything but I'll roll for you anyways.")
            user_d6 = _roll(6, rng)
        
        user_damage = user_d6 + user["damage"] #adding the damage modifier
        print(f"You rolled a {user_d6}! With your additional +{user["damage"]} modifier you deal {user_damage} damage in total.\n")
        return user_damage


# D20: dice with 20 sides
# adding modifier to D20 in this function will be problematic, 2 modifiers: for initiative and attack
# another function for initiative and attack?
# is a function even neccessary? just make a simple variable?
# maybe just a normal random D6 and D20 and then adding everything in the fight/checks?

def user_D20(rng=None):
    while True:
        try:
            roll = input("To roll a D20 dice type anything: ")
            if roll:
                user_d20 = _roll(20, rng)
            else:
                raise ValueError("Empty input")
        except ValueError:
            print("You did not type anything but I'll roll for you anyways.")
            user_d20 = _roll(20, rng)

        print(f"You rolled a {user_d20}!")
        return user_d20
            


""" Enemy's dices """
# D6: dice with 6 sides

def enemy_D6(wyrm, rng=None):
    enemy_d6 = _roll(6, rng)
    print(f"The Wyrm rolled a {enemy_d6} and deals {enemy_d6 + wyrm["damage"]} damage in total.")
    return enemy_d6


# D20: dice with 20 sides
def enemy_D20(rng=None):
    enemy_d20 = _roll(20, rng)
    print(f"The Wyrm rolled a {enemy_d20}!")
    return enemy_d20
