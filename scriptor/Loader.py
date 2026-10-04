import Misc
import Parser
from Game import Game
from Player import Player
from Room import Room

# Functions a script may use inside a room's "Commands:" block. Anything
# else is a typo and must be reported instead of being silently dropped.
KNOWN_COMMAND_FUNCTIONS = ("enable", "disable", "do")


def _text(parts):
    """Join the plain words of a parsed Name/Description (skip blocks)."""
    return " ".join(part for part in parts if isinstance(part, str))


def _script_commands(parsed_commands):
    commands = {}
    for entry in parsed_commands:
        name = entry[0]
        action = entry[1]
        functions = []
        for index in range(0, len(action), 2):
            function = action[index]
            parameters = [str(parameter) for parameter in action[index + 1]]
            functions.append((function, parameters))
        commands[name] = functions
    return commands


def build_game(script_text):
    """Parse a script and build the matching rooms and player state.

    Returns a ready-to-run Game. Script problems raise Misc.ScriptError
    with an author-readable message.
    """
    parsed = Parser.parse_script(script_text)

    rooms = {}
    for room_result in parsed:
        roomID = room_result["id"]
        if roomID in rooms:
            raise Misc.ScriptError("room '%s' is defined more than once" % roomID)

        name = _text(room_result[1]) or "default room"
        description = room_result["description"]

        connections = {}
        if "paths" in room_result:
            for path in room_result["paths"]:
                connections[path["target"]] = path["destination"]

        variables = {}
        if "local_variables" in room_result:
            for variable in room_result["local_variables"]:
                variables[str(variable[0])] = str(variable[1])

        commands = {}
        if "commands" in room_result:
            commands = _script_commands(room_result["commands"])
            for commandName, action in commands.items():
                for function, parameters in action:
                    if function not in KNOWN_COMMAND_FUNCTIONS:
                        raise Misc.ScriptError(
                            "unknown command function '%s' in room '%s', command '%s' (known functions: %s)"
                            % (function, roomID, commandName,
                               ", ".join(KNOWN_COMMAND_FUNCTIONS)))

        rooms[roomID] = Room(
            ID=roomID,
            name=name,
            desc=description,
            connections=connections,
            script_commands=commands,
            variables=variables)

    if not rooms:
        raise Misc.ScriptError("could not build game: the script defines no rooms")

    player = Player(next(iter(rooms.values())))
    return Game(rooms, player)
