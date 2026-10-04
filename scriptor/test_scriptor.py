"""Tests for the scriptor engine: parse results must match game state,
and broken scripts must raise readable ScriptError instead of crashing.

Run with:  python3 -m unittest test_scriptor -v
"""
import io
import contextlib
import os
import subprocess
import sys
import unittest

import Misc
import Parser
from Game import Game
from Item import Item
from Loader import build_game
from Player import Player
from Room import Room

SCRIPT = """
+room1:

Name: A Room
Description: a plain room {[player has r1Bar] without the bar. [else] with a bar.}

Commands:
    throw switch:
        enable .lights
        do something

Variables:
    .lights = true
    .an = off

Paths:
    north -> room2

+room2:

Name: Other Room
Description: the second room

Paths:
    south -> room1
"""

GLOBAL_COMMANDS = {
    "take": """
if self.player.loc.contains("!x!"):
    self.player.addToInv("!x!")
""",
}


def run_command(game, command):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        game.handleCommand(command)
    return out.getvalue()


def room_details(room):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        room.printDetails()
    return out.getvalue()


class ExampleUnchanged(unittest.TestCase):
    def test_example_script_still_parses(self):
        result = Parser.combined.parseString(Parser.parsed)
        self.assertEqual(result[0]["id"], "room1")
        paths = {p["target"]: p["destination"] for p in result[0]["paths"]}
        self.assertEqual(paths, {"north": "house", "south": "room2"})

    def test_main_example_runs_without_crash(self):
        here = os.path.dirname(os.path.abspath(__file__))
        proc = subprocess.run(
            [sys.executable, "Main.py"],
            input="look\nnext\nback\ntake bar\ninv\n!exit!\n",
            capture_output=True, text=True, cwd=here)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Traceback", proc.stdout + proc.stderr)
        self.assertIn("second room", proc.stdout)
        self.assertIn("you slide the bar into your pocket", proc.stdout)
        self.assertIn("Game Ended", proc.stdout)


class ParseMatchesGameState(unittest.TestCase):
    def setUp(self):
        self.parsed = Parser.parse_script(SCRIPT)
        self.game = build_game(SCRIPT)

    def test_rooms_match_parse_result(self):
        parsed_ids = [room["id"] for room in self.parsed]
        self.assertEqual(list(self.game.rooms.keys()), parsed_ids)

    def test_names_match_parse_result(self):
        self.assertEqual(self.game.rooms["room1"].name, "A Room")
        self.assertEqual(self.game.rooms["room2"].name, "Other Room")

    def test_connections_match_parse_result(self):
        for room_result in self.parsed:
            room = self.game.rooms[room_result["id"]]
            expected = {}
            if "paths" in room_result:
                expected = {p["target"]: p["destination"] for p in room_result["paths"]}
            self.assertEqual(room.connections, expected)

    def test_commands_match_parse_result(self):
        commands = self.game.rooms["room1"].script_commands
        self.assertEqual(commands, {
            "throw switch": [("enable", [".lights"]), ("do", ["something"])],
        })
        self.assertEqual(self.game.rooms["room2"].script_commands, {})

    def test_variables_match_parse_result(self):
        self.assertEqual(self.game.rooms["room1"].variables,
                         {".lights": "true", ".an": "off"})

    def test_player_starts_in_first_room(self):
        self.assertIs(self.game.player.loc, self.game.rooms["room1"])
        self.assertEqual(self.game.player.inv, [])

    def test_parsed_description_renders_like_source(self):
        # "{[player has r1Bar] without the bar. [else] with a bar.}":
        # the bar is gone from the room -> the player must have taken it.
        details = room_details(self.game.rooms["room1"])
        self.assertIn("without the bar.", details)
        self.assertNotIn("with a bar.", details)
        self.game.rooms["room1"].items.append(Item(ID="r1Bar", names=["bar"]))
        details = room_details(self.game.rooms["room1"])
        self.assertIn("with a bar.", details)
        self.assertNotIn("without the bar.", details)

    def test_movement_follows_parsed_paths(self):
        self.game.handleCommand("north")
        self.assertIs(self.game.player.loc, self.game.rooms["room2"])
        self.game.handleCommand("south")
        self.assertIs(self.game.player.loc, self.game.rooms["room1"])


class ReadableErrors(unittest.TestCase):
    def assertReadable(self, script, *fragments):
        with self.assertRaises(Misc.ScriptError) as caught:
            build_game(script)
        message = str(caught.exception)
        self.assertNotIn("Traceback", message)
        for fragment in fragments:
            self.assertIn(fragment, message)

    def test_missing_description_field(self):
        self.assertReadable("+room1:\n\nName: A Room\n",
                            "could not parse script", "Description:")

    def test_missing_name_field(self):
        self.assertReadable("+room1:\n\nDescription: hi\n",
                            "could not parse script", "Name:")

    def test_empty_script(self):
        self.assertReadable("   \n", "empty")

    def test_trailing_junk_not_silently_ignored(self):
        self.assertReadable(SCRIPT + "this is not a room",
                            "could not parse script", "this is not a room")

    def test_undefined_room_in_paths(self):
        self.assertReadable(SCRIPT.replace("north -> room2", "north -> nowhere"),
                            "room 'room1'", "'north'", "undefined room 'nowhere'")

    def test_duplicate_room_id(self):
        self.assertReadable(SCRIPT + SCRIPT, "more than once")

    def test_unknown_command_function(self):
        script = SCRIPT.replace("enable .lights", "destroy .lights")
        self.assertReadable(script, "unknown command function 'destroy'",
                            "room1", "throw switch")

    def test_duplicate_item_ids(self):
        room = Room("r1", items=[Item(ID="bar", names=["bar"]),
                                 Item(ID="bar", names=["other bar"])])
        with self.assertRaises(Misc.ScriptError) as caught:
            Game({"r1": room}, Player(room))
        self.assertIn("more than one item with ID 'bar'", str(caught.exception))

    def test_player_starting_in_undefined_room(self):
        room = Room("r1")
        stranger = Room("rX")
        with self.assertRaises(Misc.ScriptError) as caught:
            Game({"r1": room}, Player(stranger))
        self.assertIn("not one of the defined rooms", str(caught.exception))


class GameplayGuards(unittest.TestCase):
    def setUp(self):
        self.game = build_game(SCRIPT)
        self.game.global_commands.update(GLOBAL_COMMANDS)

    def test_move_out_of_bounds_does_not_crash(self):
        self.game.player.loc.connections["west"] = "nowhere"
        output = run_command(self.game, "west")
        self.assertIn("can't go that way", output)
        self.assertIs(self.game.player.loc, self.game.rooms["room1"])

    def test_unknown_command_gets_a_reply(self):
        output = run_command(self.game, "xyzzy")
        self.assertIn("don't understand", output)

    def test_command_without_argument_gets_a_reply(self):
        output = run_command(self.game, "take")
        self.assertIn("needs something to act on", output)

    def test_restart_does_not_share_state(self):
        first = build_game(SCRIPT)
        first.player.inv.append(Item(ID="stale", names=["stale"]))
        first.rooms["room1"].items.append(Item(ID="staleRoom", names=["stale"]))
        first.rooms["room1"].connections["west"] = "room2"

        second = build_game(SCRIPT)
        self.assertEqual(second.player.inv, [])
        self.assertEqual(second.rooms["room1"].items, [])
        self.assertEqual(second.rooms["room1"].connections, {"north": "room2"})

    def test_default_arguments_are_not_shared(self):
        room_a, room_b = Room("a"), Room("b")
        room_a.items.append("x")
        room_a.connections["n"] = "b"
        self.assertEqual(room_b.items, [])
        self.assertEqual(room_b.connections, {})

        player_a, player_b = Player(room_a), Player(room_a)
        player_a.inv.append("x")
        self.assertEqual(player_b.inv, [])

        item_a, item_b = Item(), Item()
        item_a.names.append("x")
        self.assertEqual(item_b.names, [])


if __name__ == "__main__":
    unittest.main()
