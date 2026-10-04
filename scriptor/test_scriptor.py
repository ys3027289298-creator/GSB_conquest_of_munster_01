import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import Parser
from Misc import ScriptError
from Game import Game
from Player import Player
from Room import Room
from Item import Item

VALID_SCRIPT = """
+hall:

Name: Grand Hall
Description: A vast hall. {[player has coin] The slot is empty. [else] A coin glints.}

Commands:
    lights on:
        enable .lights

    lights off:
        disable .lights

    wander:
        goto kitchen

Variables:
    .lights = false

Paths:
    north -> kitchen

+kitchen:

Name: Kitchen
Description: A small kitchen.

Paths:
    back -> hall
"""


def run_game(game, commands):
    inputs = iter(list(commands) + ["!exit!"])
    output = io.StringIO()
    with patch("builtins.input", lambda: next(inputs)), redirect_stdout(output):
        game.gameLoop()
    return output.getvalue()


class ParseBuildTest(unittest.TestCase):
    def test_builds_rooms_player_and_state(self):
        game = Parser.build_game(VALID_SCRIPT)
        self.assertEqual(set(game.rooms), {"hall", "kitchen"})
        hall = game.rooms["hall"]
        self.assertEqual(hall.name, "Grand Hall")
        self.assertEqual(hall.variables, {"lights": False})
        self.assertEqual(hall.connections, {"north": "kitchen"})
        self.assertEqual(game.rooms["kitchen"].connections, {"back": "hall"})
        self.assertEqual(set(hall.commands), {"lights on", "lights off", "wander"})
        self.assertIs(game.player.loc, hall)

    def test_parse_results_match_game_state(self):
        game = Parser.build_game(VALID_SCRIPT)
        parsed = Parser.parse_script(VALID_SCRIPT)
        by_id = {room["id"]: room for room in parsed}
        self.assertEqual(set(by_id), set(game.rooms))
        for room_id, parsed_room in by_id.items():
            room = game.rooms[room_id]
            self.assertEqual(room.name, " ".join(parsed_room["name"]))
            reparsed = Parser.desc_block.parseString(room.desc)
            self.assertEqual(reparsed[0].asList(), parsed_room["description"].asList())
            if "paths" in parsed_room:
                expected = {p["target"]: p["destination"] for p in parsed_room["paths"]}
            else:
                expected = {}
            self.assertEqual(room.connections, expected)
            if "commands" in parsed_room:
                self.assertEqual(set(room.commands), {c[0] for c in parsed_room["commands"]})

    def test_conditional_description_round_trip(self):
        game = Parser.build_game(VALID_SCRIPT)
        hall = game.rooms["hall"]
        self.assertIn("{[player has coin]", hall.desc)
        self.assertIn("[else]", hall.desc)
        game.player.inv.append(Item(ID="coin", names=["coin"]))
        output = io.StringIO()
        with redirect_stdout(output):
            hall.printDetails(game.player)
        self.assertIn("The slot is empty.", output.getvalue())
        game.player.inv.clear()
        output = io.StringIO()
        with redirect_stdout(output):
            hall.printDetails(game.player)
        self.assertIn("A coin glints.", output.getvalue())


class CommandExecutionTest(unittest.TestCase):
    def test_commands_update_game_state(self):
        game = Parser.build_game(VALID_SCRIPT)
        hall = game.rooms["hall"]
        exec(hall.commands["lights on"], {"self": game})
        self.assertIs(hall.variables["lights"], True)
        exec(hall.commands["lights off"], {"self": game})
        self.assertIs(hall.variables["lights"], False)
        exec(hall.commands["wander"], {"self": game})
        self.assertIs(game.player.loc, game.rooms["kitchen"])

    def test_game_loop_moves_and_reports_unknown_command(self):
        game = Parser.build_game(VALID_SCRIPT)
        output = run_game(game, ["north", "blah"])
        self.assertIs(game.player.loc, game.rooms["kitchen"])
        self.assertIn("Sorry, I don't understand", output)


class ErrorScriptTest(unittest.TestCase):
    def test_missing_description(self):
        with self.assertRaises(ScriptError) as ctx:
            Parser.build_game("+r1:\n\nName: Only Name\n")
        self.assertIn("Description", str(ctx.exception))
        self.assertIn("r1", str(ctx.exception))

    def test_missing_name(self):
        with self.assertRaises(ScriptError) as ctx:
            Parser.build_game("+r1:\n\nDescription: no name here\n")
        self.assertIn("Name", str(ctx.exception))

    def test_unknown_content_is_not_silently_dropped(self):
        with self.assertRaises(ScriptError) as ctx:
            Parser.parse_script(VALID_SCRIPT + "\nthis is total garbage @@##\n")
        self.assertIn("line", str(ctx.exception))

    def test_unknown_command_action(self):
        script = "+r1:\n\nName: N\nDescription: d\n\nCommands:\n    pull lever:\n        do something\n"
        with self.assertRaises(ScriptError) as ctx:
            Parser.build_game(script)
        self.assertIn("do", str(ctx.exception))
        self.assertIn("pull lever", str(ctx.exception))

    def test_undefined_room_in_path(self):
        script = "+r1:\n\nName: N\nDescription: d\n\nPaths:\n    north -> nowhere\n"
        with self.assertRaises(ScriptError) as ctx:
            Parser.build_game(script)
        self.assertIn("nowhere", str(ctx.exception))

    def test_undefined_room_in_goto_command(self):
        script = "+r1:\n\nName: N\nDescription: d\n\nCommands:\n    jump:\n        goto nowhere\n"
        with self.assertRaises(ScriptError) as ctx:
            Parser.build_game(script)
        self.assertIn("nowhere", str(ctx.exception))

    def test_duplicate_room(self):
        script = VALID_SCRIPT + "\n+hall:\n\nName: Again\nDescription: dup\n"
        with self.assertRaises(ScriptError) as ctx:
            Parser.build_game(script)
        self.assertIn("hall", str(ctx.exception))

    def test_undefined_room_in_hand_built_game(self):
        room = Room("r1", connections={"next": "r2"})
        with self.assertRaises(ScriptError) as ctx:
            Game({"r1": room}, Player(room))
        self.assertIn("r2", str(ctx.exception))

    def test_duplicate_items(self):
        room = Room("r1", items=[Item(ID="dup", names=["a"]), Item(ID="dup", names=["b"])])
        with self.assertRaises(ScriptError) as ctx:
            Game({"r1": room}, Player(room))
        self.assertIn("dup", str(ctx.exception))

    def test_player_must_start_in_game_room(self):
        with self.assertRaises(ScriptError):
            Game({"r1": Room("r1")}, Player(Room("elsewhere")))


class MovementTest(unittest.TestCase):
    def test_goto_rejects_non_room(self):
        player = Player(Room("r1"))
        with self.assertRaises(ScriptError):
            player.goto("nowhere-string")
        with self.assertRaises(ScriptError):
            player.goto(None)

    def test_out_of_bounds_move_is_readable_not_crash(self):
        rooms = {"r1": Room("r1", connections={"north": "r2"}), "r2": Room("r2")}
        game = Game(rooms, Player(rooms["r1"]))
        game.rooms["r1"].connections["north"] = "void"
        output = run_game(game, ["north"])
        self.assertIn("can't go that way", output)
        self.assertIs(game.player.loc, game.rooms["r1"])


class RestartTest(unittest.TestCase):
    def test_restart_restores_initial_state(self):
        game = Parser.build_game(VALID_SCRIPT)
        hall = game.rooms["hall"]
        exec(hall.commands["lights on"], {"self": game})
        game.player.goto(game.rooms["kitchen"])
        game.player.inv.append(Item(ID="coin", names=["coin"]))
        hall.items.append(Item(ID="junk", names=["junk"]))

        game.restart()

        self.assertIs(game.player.loc, game.rooms["hall"])
        self.assertIs(game.rooms["hall"].variables["lights"], False)
        self.assertEqual(game.player.inv, [])
        self.assertEqual(game.rooms["hall"].items, [])

    def test_restart_is_repeatable(self):
        game = Parser.build_game(VALID_SCRIPT)
        game.rooms["hall"].variables["lights"] = True
        game.restart()
        game.rooms["hall"].variables["lights"] = True
        game.player.goto(game.rooms["kitchen"])
        game.restart()
        self.assertIs(game.rooms["hall"].variables["lights"], False)
        self.assertIs(game.player.loc, game.rooms["hall"])

    def test_fresh_game_not_polluted_by_previous_one(self):
        game1 = Parser.build_game(VALID_SCRIPT)
        game1.rooms["hall"].items.append(Item(ID="junk", names=["junk"]))
        game1.player.inv.append(Item(ID="junk2", names=["junk2"]))
        game2 = Parser.build_game(VALID_SCRIPT)
        self.assertEqual(game2.rooms["hall"].items, [])
        self.assertEqual(game2.player.inv, [])

    def test_no_shared_mutable_defaults(self):
        room_a, room_b = Room("a"), Room("b")
        room_a.items.append(Item(ID="leaked"))
        self.assertEqual(room_b.items, [])
        room_a.connections["x"] = "y"
        self.assertEqual(room_b.connections, {})
        del room_a.connections["x"]
        player_a = Player(room_a)
        player_b = Player(room_b)
        player_a.inv.append(Item(ID="other"))
        self.assertEqual(player_b.inv, [])
        game_a = Game({"a": room_a}, player_a)
        game_b = Game({"b": room_b}, player_b)
        game_a.global_commands["x"] = "leaked"
        self.assertEqual(game_b.global_commands, {})
        item_a, item_b = Item(), Item()
        item_a.names.append("leaked")
        self.assertEqual(item_b.names, [])


class MainExampleTest(unittest.TestCase):
    def test_main_example_runs_unchanged(self):
        here = os.path.dirname(os.path.abspath(__file__))
        result = subprocess.run(
            [sys.executable, "Main.py"],
            input="look\n!exit!\n",
            capture_output=True,
            text=True,
            cwd=here,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("first room", result.stdout)
        self.assertIn("Game Ended", result.stdout)


if __name__ == "__main__":
    unittest.main()
