import re
from html.parser import HTMLParser
from shutil import get_terminal_size

import pyquest.game
from pyquest.errors import MissingObjectError, QuestError, ScriptError, UndefinedJumpError

__author__ = "Adrian Welcker"
__copyright__ = """Copyright 2018 Adrian Welcker

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

# Safety net for runaway `while` loops in game scripts.
MAX_LOOP_ITERATIONS = 100000


class QuestValue:
    """Union[str, int, float], sort of."""
    def __init__(self, value):
        if not (isinstance(value, int) or isinstance(value, float) or isinstance(value, str)):
            raise TypeError("QuestValue cannot accept type " + str(type(value)))
        self._value = value

    @staticmethod
    def _unwrap(other):
        if isinstance(other, QuestValue):
            return other._value
        return other

    def __add__(self, other):
        if (isinstance(self._value, int) or isinstance(self._value, float)) and \
                (isinstance(other, int) or isinstance(other, float)):
            return self._value + other
        elif (isinstance(self._value, int) or isinstance(self._value, float)) and \
                isinstance(other, QuestValue):
            if isinstance(other._value, int) or isinstance(other._value, float):
                return self._value + other._value
            elif isinstance(other._value, str):
                return str(self._value) + other._value
        elif isinstance(self._value, str) and isinstance(other, str):
            return self._value + other
        elif isinstance(self._value, str):
            return self._value + str(other)
        else:
            raise TypeError("QuestValue: operation add not supported for self (" +
                            str(type(self._value)) + ") and other (" + str(type(other)) + ").")

    def __radd__(self, other):
        if (isinstance(other, int) or isinstance(other, float)) and \
                (isinstance(self._value, int) or isinstance(self._value, float)):
            return other + self._value
        elif isinstance(other, QuestValue) and (isinstance(self._value, int) or
                                                isinstance(self._value, float)):
            if isinstance(other._value, int) or isinstance(other._value, float):
                return other._value + self._value
            elif isinstance(other._value, str):
                return str(other._value) + str(self._value)
        elif isinstance(other, str) and isinstance(self._value, str):
            return other + self._value
        elif isinstance(self._value, str):
            return str(other) + self._value
        elif isinstance(other, str):
            return other + str(self._value)
        elif isinstance(other, QuestValue):
            return repr(other._value) + repr(self._value)
        else:
            raise TypeError("QuestValue: operation add not supported for other (" +
                            str(type(other)) + ") and self (" + str(type(self._value)) + ").")

    def __sub__(self, other):
        return self._value - self._unwrap(other)

    def __rsub__(self, other):
        return self._unwrap(other) - self._value

    def __mul__(self, other):
        return self._value * self._unwrap(other)

    def __rmul__(self, other):
        return self._unwrap(other) * self._value

    def __eq__(self, other):
        return self._value == self._unwrap(other)

    def __ne__(self, other):
        return self._value != self._unwrap(other)

    def __lt__(self, other):
        return self._value < self._unwrap(other)

    def __le__(self, other):
        return self._value <= self._unwrap(other)

    def __gt__(self, other):
        return self._value > self._unwrap(other)

    def __ge__(self, other):
        return self._value >= self._unwrap(other)

    def __bool__(self):
        return bool(self._value)

    def __hash__(self):
        return hash(self._value)

    def __int__(self):
        return int(self._value)

    def __float__(self):
        return float(self._value)

    def __repr__(self):
        if isinstance(self._value, str):
            return self._value
        else:
            return repr(self._value)

    def __str__(self):
        if isinstance(self._value, str):
            return self._value
        else:
            return str(self._value)


class QuestList(list):
    def __init__(self, type_):
        super(QuestList, self).__init__()
        self._type = type_


class ScriptEngine:
    def __init__(self, game):
        self.game = game
        self.functions = {}
        # Keys of `firsttime` blocks that have already fired, so the same
        # event is never executed twice within one playthrough.
        self.firsttime_done = set()
        self.globals = {}

    def define_function(self, name, *params, body):
        self.functions[name] = Function(name, *params, body=body)

    def is_function(self, name):
        return name in self.functions

    def prep(self):
        """Build the global namespace scripts run in.

        Unlike the old implementation this does not touch this module's own
        globals, so several games (or a restarted game) can coexist.
        """
        namespace = {
            "msg": msg,
            "NewStringList": NewStringList,
            "list_add": list_add,
            "list_remove": list_remove,
            "HasInt": HasInt,
            "HasString": HasString,
            "TypeOf": TypeOf,
            "LengthOf": len,
            "GetObject": GetObject,
            "MoveObject": MoveObject,
            "JS": JS,
            "false": False,
            "true": True,
            "null": None,
        }
        namespace.update(self.game.objects)
        namespace.update(self.functions)
        self.globals = namespace

    def run_safe(self, script, **kwparams):
        """Run a script, recovering from any expected engine failure.

        Returns None on success, or the caught QuestError. The error is also
        recorded on the game so the caller can inspect or report it; the game
        itself stays usable afterwards.
        """
        try:
            script(**kwparams)
        except QuestError as err:
            self.game.last_error = err
            return err
        except NameError as err:
            # A bare name lookup failed inside a script expression.
            wrapped = ScriptError("Unresolved name in script %s: %s" % (script.name, err))
            self.game.last_error = wrapped
            return wrapped
        return None


class Function:
    def __init__(self, name, *params, body):
        self.name = name
        self.parameters = params
        if isinstance(body, Script):
            self.body = body
        else:
            self.body = Script("functions->" + name, body)

    def __call__(self, *params):
        return self.body(**dict(zip(self.parameters, params)))


class ReturnSignal(Exception):
    """Internal control-flow exception implementing `return`."""
    def __init__(self, value=None):
        super().__init__()
        self.value = value


_CALL_RE = re.compile(r"^([A-Za-z_]\w*)\s*\(")
_IF_RE = re.compile(r"^if\s*\((.*)\)\s*\{\s*$")
_FOREACH_RE = re.compile(r"^foreach\s*\(\s*(\w+)\s*,\s*(.+)\)\s*\{\s*$")
_WHILE_RE = re.compile(r"^while\s*\((.*)\)\s*\{\s*$")
_EQUALS_RE = re.compile(r"(?<![<>=!])=(?!=)")


class Script:
    def __init__(self, name, code):
        self.name = name
        # Empty scripts (e.g. `<attr name="ring" type="script"></attr>`) are
        # legal; normalise them to an empty body instead of crashing.
        self.code = code or ""

    def __call__(self, **kwparams):
        engine = pyquest.game.the_game.script_engine
        env = dict(engine.globals)
        env.update(kwparams)
        try:
            self._exec_lines(self.code.splitlines(), env)
        except ReturnSignal as ret:
            return ret.value
        return None

    def _location(self, index):
        game = pyquest.game.the_game
        game_name = getattr(game, "name", "game")
        return "{}->{}: l{}".format(game_name, self.name, index)

    def _eval(self, source, env, index):
        source = _EQUALS_RE.sub("==", source)
        return eval(compile(source, self._location(index), 'eval'), env)

    def _exec_stmt(self, line, env, index):
        if line.startswith("list add "):
            line = "list_add(" + self._call_args(line[len("list add "):]) + ")"
        elif line.startswith("list remove "):
            line = "list_remove(" + self._call_args(line[len("list remove "):]) + ")"
        else:
            call = _CALL_RE.match(line)
            if call is not None and call.group(1) not in env:
                raise UndefinedJumpError(call.group(1))
        exec(compile(line, self._location(index), 'exec'), env)

    @staticmethod
    def _call_args(source):
        source = source.strip()
        if source.startswith("(") and source.endswith(")"):
            source = source[1:-1]
        return source

    @staticmethod
    def _block_range(lines, index):
        """Given the index of a header line ending in '{', return (body, next).

        body is the list of lines inside the braces, next the index of the
        first line after the matching '}'.
        """
        depth = 1
        cursor = index + 1
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            if stripped.endswith("{"):
                depth += 1
            elif stripped == "}":
                depth -= 1
                if depth == 0:
                    return lines[index + 1:cursor], cursor + 1
            cursor += 1
        raise ScriptError("Unterminated block starting at line " + str(index))

    def _exec_lines(self, lines, env):
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line or line.startswith("//"):
                index += 1
                continue
            if line == "}":
                raise ScriptError("Unexpected '}' at line " + str(index))

            matched = _IF_RE.match(line)
            if matched is not None:
                body, index = self._block_range(lines, index)
                else_body = None
                if index < len(lines) and lines[index].strip() == "else {":
                    else_body, index = self._block_range(lines, index)
                if self._eval(matched.group(1), env, index):
                    self._exec_lines(body, env)
                elif else_body is not None:
                    self._exec_lines(else_body, env)
                continue
            if line == "else {":
                raise ScriptError("'else' without matching 'if' at line " + str(index))

            if line == "firsttime {":
                start = index
                body, index = self._block_range(lines, index)
                otherwise_body = None
                if index < len(lines) and lines[index].strip() == "otherwise {":
                    otherwise_body, index = self._block_range(lines, index)
                key = self.name + ":" + str(start)
                engine = pyquest.game.the_game.script_engine
                if key not in engine.firsttime_done:
                    engine.firsttime_done.add(key)
                    self._exec_lines(body, env)
                elif otherwise_body is not None:
                    self._exec_lines(otherwise_body, env)
                continue
            if line == "otherwise {":
                raise ScriptError("'otherwise' without 'firsttime' at line " + str(index))

            matched = _FOREACH_RE.match(line)
            if matched is not None:
                variable, iterable_src = matched.group(1), matched.group(2)
                body, index = self._block_range(lines, index)
                for value in self._eval(iterable_src, env, index):
                    env[variable] = value
                    self._exec_lines(body, env)
                continue

            matched = _WHILE_RE.match(line)
            if matched is not None:
                condition_src = matched.group(1)
                body, index = self._block_range(lines, index)
                iterations = 0
                while self._eval(condition_src, env, index):
                    self._exec_lines(body, env)
                    iterations += 1
                    if iterations > MAX_LOOP_ITERATIONS:
                        raise ScriptError("Loop in script %s exceeded %d iterations"
                                          % (self.name, MAX_LOOP_ITERATIONS))
                continue

            if line == "return":
                raise ReturnSignal(None)
            if line.startswith("return "):
                raise ReturnSignal(self._eval(line[len("return "):], env, index))

            self._exec_stmt(line, env, index)
            index += 1

    def __str__(self):
        return "({} characters of code)".format(len(self.code))

    def __repr__(self):
        return "Script(name=%r, code=%r)" % (self.name, self.code)


class Verb:
    def __init__(self, verb):
        self.verb = verb


class MarkupStripper(HTMLParser):
    def error(self, message):
        print("[** HTML Markup Stripper Error:", message, "**]")

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = False
        self.fed = []

    def handle_data(self, data):
        self.fed.append(data)

    def get_data(self):
        return ''.join(self.fed)


def demarkup(text):
    stripper = MarkupStripper()
    stripper.feed(text.replace("<br/>", "\n").replace("<br>", "\n"))
    return stripper.get_data()


# pylint:disable=invalid-name
class FakeJS:
    """Provides methods for "JS.something( )" calls withing ASL source.

    Since we operate on a terminal instead of an HTML output,
    most of this does nothing.
    """
    def __init__(self):
        self.alignment = "left"

    def createNewDiv(self, align):
        """Sets the alignment to the given alignment."""
        self.alignment = align

    def StartOutputSection(self, name):
        """Does nothing."""
        pass

    def EndOutputSection(self, name):
        """Does nothing."""
        pass

    def HideOutputSection(self, name):
        """Does nothing."""
        pass


def msg(text):
    """Prints text to the screen, using the currently active alignment."""
    for line in text.splitlines():
        if JS.alignment == "left":
            print(demarkup(line))
        elif JS.alignment == "center":
            print(demarkup(line).center(get_terminal_size()[0] - 1))
        else:
            print(demarkup(line).rjust(get_terminal_size()[0] - 1))


def NewStringList():
    return QuestList("string")


def list_add(list_, value):
    list_.append(value)


def list_remove(list_, value):
    if value in list_:
        list_.remove(value)


def GetObject(name):
    """Look up an object in the world model, raising MissingObjectError."""
    return pyquest.game.the_game.get_object(name)


def MoveObject(obj, destination):
    """Move an object to a new parent, validating both ends first.

    The world state is only mutated once both objects are known to exist,
    so a failed move never leaves the world in a half-updated state.
    """
    game = pyquest.game.the_game
    if isinstance(obj, str):
        obj = game.get_object(obj)
    if isinstance(destination, str):
        destination = game.get_object(destination)
    obj.parent = destination


def HasInt(obj, tag):
    try:
        return isinstance(getattr(obj, tag), int)
    except AttributeError:
        return False


def HasString(obj, tag):
    try:
        return isinstance(getattr(obj, tag), str)
    except AttributeError:
        return False


def TypeOf(obj):
    if isinstance(obj, QuestValue):
        if isinstance(obj._value, str):
            return "string"
        elif isinstance(obj._value, int):
            return "int"
    elif isinstance(obj, str):
        return "string"
    elif isinstance(obj, int):
        return "int"
    elif isinstance(obj, QuestList):
        return obj._type + "list"
    elif isinstance(obj, list):
        if len(obj) > 0:
            if isinstance(obj[0], str):
                return "stringlist"
            elif isinstance(obj[0], int):
                return "intlist"


JS = FakeJS()
false = False
true = True
null = None
LengthOf = len
