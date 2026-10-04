import re

from pyparsing import *

from Misc import ScriptError

if_condition = (
    Suppress(Literal("[")) +
    Word(printables).setResultsName("subject") +
    Word(alphanums).setResultsName("verb") +
    Optional(
        Word(alphanums).setResultsName("object")
    ) +
    Suppress(Literal("]"))
)

else_condition = (
    Suppress(Literal("[else]"))
)

condition_text = (
    SkipTo(Literal("[") | Literal("}")).setParseAction(lambda t: t[0].strip())
)

condition_block = Group(
    Suppress(Literal("{")) +
    Group(
        if_condition.setResultsName("condition") +
        condition_text.setResultsName("condition_text")
    ).setResultsName("if_condition") +
    Group(
        Optional(
            else_condition +
            condition_text.setResultsName("condition_text")
        )
    ).setResultsName("else_condition") +
    Suppress(Literal("}"))
)

desc_block = Group(
    OneOrMore(
        condition_block |
        Word(printables)
    )
)

local_variable = (
    Suppress(Literal(".")) +
    Word(alphanums).setParseAction(lambda t: "." + t[0])
)

room_variables = Group(
    Suppress(
        Literal("Variables:") +
        LineEnd()
    ) +
    OneOrMore(
        Group(
            local_variable +
            Suppress(Literal("="))+
            Word(alphanums) +
            Suppress(LineEnd())
        )
    )
).setResultsName("local_variables")

path = Group(
    Word(alphanums).setResultsName("target") +
    Suppress(Literal("->")) +
    Word(alphanums).setResultsName("destination")
)

command = Group(
    OneOrMore(Word(alphanums)).setParseAction(lambda t: " ".join(t)) +
    Suppress(
        Literal(":") +
        LineEnd()
    ) +
    Group(OneOrMore(
        Word(alphanums).setResultsName("function") +
        Group(OneOrMore(
            local_variable |
            path |
            Word(alphanums) +
            Suppress(LineEnd())
        )).setResultsName("parameters")
    )) +
    Suppress(OneOrMore(LineEnd()))
)

room_commands = Group(
    Suppress(
        Literal("Commands:") +
        LineEnd()
    ) +
    OneOrMore(command)
).setResultsName("commands")

room_ID = (
    Suppress(Literal("+")) +
    Word(alphanums).setResultsName("id") +
    Suppress(Literal(":")) +
    Suppress(OneOrMore(LineEnd()))
)
# room_name = Literal("Name:") + desc_block + Suppress(OneOrMore(LineEnd()))
room_name = (
    Suppress(Literal("Name:")) +
    SkipTo(LineEnd()).setResultsName("name").setParseAction(lambda t: desc_block.parseString(str(t[0])))
)

room_desc = (
    Suppress(Literal("Description:")) +
    SkipTo(LineEnd()).setParseAction(lambda t: desc_block.parseString(str(t[0]))[0])
).setResultsName("description")
# room_desc = Literal("Description:") + desc_block + Suppress(OneOrMore(LineEnd()))
# room_desc = Literal("Description:") + OneOrMore(Word(printables)) + Suppress(LineEnd())

room_paths = Group(
    Suppress(Literal("Paths:") + LineEnd()) +
    OneOrMore(
        path +
        Suppress(LineEnd())
    )
).setResultsName("paths")

room = Group(
    room_ID +
    room_name &
    room_desc &
    Optional(room_commands) &
    Optional(room_variables) &
    Optional(room_paths)
)

combined = OneOrMore(
    OneOrMore(
        room
    )
)

parsed = """
+room1:

Name: A Room
Description: sfdlk jklf jdksl fds {[dfsj f] djfd sds [else] slkd sd dsfaf ksd } hi

Commands:
    throw switch:
        enable .lights
        do something

    throw switch2:
        enable .lights
        do something

Variables:
    .lights = true
    .an = off

Paths:
    north -> house
    south -> room2
"""
# print(local_variable.parseString(".hi"))

# print(roomCommands.parseString(parsed))

print(combined.parseString(parsed)[0])

# roomDesc

"""
TODO: need parsed condition block to be tuple where first item is key (but not
dictionary because can have duplicates). For the moment, since there currently
arent any other description-based entities beside conditional blocks.
"""
# with open("testInput2") as raw:
    # parsed = parseFile(raw)

# parsed = desc_block.parseString("sfdlk jklf jdksl fds {[dfsj f] djfd sds [else] slkd sd dsfaf ksd } hi")

# print(parsed)

# print(desc_block.parseString("sfdlk jklf jdksl fds {[dfsj f] djfd sds [else] slkd sd dsfaf ksd } hi"))
# print(type(parsed.asList()[0]))

KNOWN_ACTIONS = ("enable", "disable", "goto")

_room_header = re.compile(r"^[ \t]*\+(\w+)[ \t]*:[ \t]*$", re.MULTILINE)


def parse_script(text):
    _check_required_fields(text)
    try:
        return combined.parseString(text, parseAll=True)
    except ParseException as exc:
        raise ScriptError("script error at line {}: {}".format(exc.lineno, exc.msg)) from exc


def _check_required_fields(text):
    headers = list(_room_header.finditer(text))
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.end():end]
        line = text.count("\n", 0, header.start()) + 1
        for field in ("Name:", "Description:"):
            if not re.search(r"^[ \t]*" + re.escape(field), block, re.MULTILINE):
                raise ScriptError(
                    "room '{}' is missing required field '{}' (line {})".format(header.group(1), field, line)
                )


def build_game(text):
    from Game import Game
    from Player import Player
    from Room import Room

    parsed = parse_script(text)
    rooms = {}
    goto_refs = []
    for parsed_room in parsed:
        room_id = parsed_room["id"]
        if room_id in rooms:
            raise ScriptError("duplicate room '{}'".format(room_id))
        connections = _build_connections(room_id, parsed_room)
        rooms[room_id] = Room(
            ID = room_id,
            name = " ".join(parsed_room["name"]),
            desc = _desc_to_text(parsed_room["description"]),
            commands = _build_commands(room_id, parsed_room, connections, goto_refs),
            connections = connections,
            variables = _build_variables(room_id, parsed_room),
        )
    for room_id, command_name, destination in goto_refs:
        if destination not in rooms:
            raise ScriptError(
                "command '{}' in room '{}' goes to undefined room '{}'".format(command_name, room_id, destination)
            )
    player = Player(rooms[next(iter(rooms))])
    return Game(rooms, player)


def _desc_to_text(tokens):
    parts = []
    for token in tokens:
        if isinstance(token, str):
            parts.append(token)
        else:
            condition = token["if_condition"]
            text = "[{} {}".format(condition["subject"], condition["verb"])
            if "object" in condition:
                text += " " + condition["object"]
            text += "]"
            if condition["condition_text"]:
                text += " " + condition["condition_text"]
            else_condition = token["else_condition"]
            if "condition_text" in else_condition and else_condition["condition_text"]:
                text += " [else] " + else_condition["condition_text"]
            parts.append("{" + text + "}")
    return " ".join(parts)


def _build_variables(room_id, parsed_room):
    variables = {}
    if "local_variables" not in parsed_room:
        return variables
    for name, value in parsed_room["local_variables"]:
        name = name.lstrip(".")
        if name in variables:
            raise ScriptError("duplicate variable '.{}' in room '{}'".format(name, room_id))
        variables[name] = _parse_value(value)
    return variables


def _parse_value(value):
    if value == "true":
        return True
    if value == "false":
        return False
    return value


def _build_connections(room_id, parsed_room):
    connections = {}
    if "paths" not in parsed_room:
        return connections
    for path in parsed_room["paths"]:
        if path["target"] in connections:
            raise ScriptError("duplicate path '{}' in room '{}'".format(path["target"], room_id))
        connections[path["target"]] = path["destination"]
    return connections


def _build_commands(room_id, parsed_room, connections, goto_refs):
    commands = {}
    if "commands" not in parsed_room:
        return commands
    for parsed_command in parsed_room["commands"]:
        name = parsed_command[0]
        if name in commands or name in connections:
            raise ScriptError("duplicate command '{}' in room '{}'".format(name, room_id))
        actions = parsed_command[1]
        snippets = []
        index = 0
        while index < len(actions):
            snippets.append(_action_to_code(room_id, name, actions[index], actions[index + 1], goto_refs))
            index += 2
        commands[name] = "\n".join(snippets)
    return commands


def _action_to_code(room_id, command_name, function, parameters, goto_refs):
    if function in ("enable", "disable"):
        value = function == "enable"
        lines = []
        for parameter in parameters:
            if not (isinstance(parameter, str) and parameter.startswith(".")):
                raise ScriptError(
                    "action '{}' in command '{}' of room '{}' expects a .variable, got '{}'".format(
                        function, command_name, room_id, parameter)
                )
            lines.append("self.player.loc.variables[{!r}] = {!r}".format(parameter[1:], value))
        return "\n".join(lines)
    if function == "goto":
        if len(parameters) != 1:
            raise ScriptError(
                "action 'goto' in command '{}' of room '{}' expects exactly one target".format(command_name, room_id)
            )
        target = parameters[0]
        if isinstance(target, str):
            destination = target
        elif "destination" in target:
            destination = target["destination"]
        else:
            raise ScriptError(
                "action 'goto' in command '{}' of room '{}' has an invalid target".format(command_name, room_id)
            )
        goto_refs.append((room_id, command_name, destination))
        return "self.player.goto(self.rooms[{!r}])".format(destination)
    raise ScriptError(
        "unknown action '{}' in command '{}' of room '{}'".format(function, command_name, room_id)
    )
