"""Reproduce the six reported failure modes and show what the user now sees.

Run with:  python3 reproduce_bugs.py

Each scenario prints either a readable error message (expected after the
fixes) or the old behaviour (crash / silent failure) if the bug is still
present.
"""
import io
import contextlib

from Game import Game
from Item import Item
from Loader import build_game
from Misc import ScriptError
from Player import Player
from Room import Room

GLOBAL_COMMANDS = {
    "take": """
if self.player.loc.contains("!x!"):
    self.player.addToInv("!x!")
""",
}

TWO_ROOMS = """
+room1:

Name: A Room
Description: a plain room

Paths:
    north -> room2

+room2:

Name: Other
Description: second room

Paths:
    south -> room1
"""


def show(title, function):
    print("=" * 70)
    print(title)
    print("-" * 70)
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            function()
    except ScriptError as error:
        print("readable ScriptError:\n  %s" % error)
        if out.getvalue().strip():
            print("output:", out.getvalue().strip())
    except Exception as error:
        print("CRASH %s: %s" % (type(error).__name__, error))
    else:
        text = out.getvalue().strip()
        print(text if text else "(silently ignored, no error and no output)")


def missing_fields():
    # Room without a Description: field.
    build_game("+room1:\n\nName: A Room\n")


def undefined_room():
    # Exit points at a room the script never defines.
    build_game(TWO_ROOMS.replace("north -> room2", "north -> nowhere"))


def duplicate_items():
    room = Room("r1", items=[
        Item(ID="bar", names=["bar"]),
        Item(ID="bar", names=["another bar"]),
    ])
    Game({"r1": room}, Player(room))


def unknown_command():
    # "destroy" is not one of the language's command functions, and a
    # trailing typo line used to be silently dropped by the parser.
    script = TWO_ROOMS + "oops this is not a room"
    build_game(script)


def unknown_command_function():
    script = """
+room1:

Name: A Room
Description: a plain room

Commands:
    throw switch:
        destroy .lights
"""
    build_game(script)


def move_out_of_bounds():
    game = build_game(TWO_ROOMS)
    game.player.loc.connections["west"] = "nowhere"
    before = game.player.loc
    game.handleCommand("west")
    assert game.player.loc is before, "player location changed through a bad exit"


def restart_state_bleed():
    first = build_game(TWO_ROOMS)
    first.player.inv.append(Item(ID="stale", names=["stale item"]))
    first.rooms["room1"].items.append(Item(ID="staleRoom", names=["stale room item"]))

    second = build_game(TWO_ROOMS)
    if second.player.inv:
        print("state bled into the restarted player's inventory: %r" % second.player.inv)
    elif second.rooms["room1"].items:
        print("state bled into the restarted room's items: %r" % second.rooms["room1"].items)
    else:
        print("restarted game starts clean (fresh inventory and empty room items)")


def command_without_argument():
    game = build_game(TWO_ROOMS)
    game.global_commands.update(GLOBAL_COMMANDS)
    game.handleCommand("take")


if __name__ == "__main__":
    show("1. script with a missing field", missing_fields)
    show("2. exit leading to an undefined room", undefined_room)
    show("3. duplicate item IDs in one room", duplicate_items)
    show("4a. parser silently ignoring trailing junk", unknown_command)
    show("4b. unknown command function in a script", unknown_command_function)
    show("4c. 'take' with no argument", command_without_argument)
    show("5. player moving out of bounds", move_out_of_bounds)
    show("6. state bleeding into a restarted game", restart_state_bleed)
