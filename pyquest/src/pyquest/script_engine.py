import sys
from html.parser import HTMLParser
from shutil import get_terminal_size

import pyquest.game

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

    def __bool__(self):
        return bool(self._value)

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

    def __hash__(self):
        return hash(self._value)

    # def __instancecheck__(self, instance):
    #     return isinstance(self._value, instance)

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


#: Maximum nesting depth for scripts calling scripts. Prevents runaway
#: "looping events" (a script or function that (in)directly invokes itself)
#: from crashing the interpreter with a RecursionError.
MAX_SCRIPT_DEPTH = 100


class ScriptEngine:
    """Executes ASL scripts on behalf of one QuestGame.

    All state produced by running scripts (variables, fired one-shot events)
    lives on the engine instance, never in module globals, so concurrent or
    successive games cannot leak state into each other.
    """
    def __init__(self, game):
        self.game = game
        self.functions = {}
        self.namespace = {}
        self.events_fired = set()
        self._call_depth = 0
        self._block_counter = 0
        self.reset_namespace()

    def reset_namespace(self):
        """(Re)build the variable namespace with the script built-ins."""
        self.namespace = {
            "msg": msg,
            "JS": JS,
            "NewStringList": NewStringList,
            "list_add": list_add,
            "HasInt": HasInt,
            "HasString": HasString,
            "TypeOf": TypeOf,
            "LengthOf": len,
            "true": True,
            "false": False,
            "null": None,
        }

    def define_function(self, name, *params, body):
        self.functions[name] = Function(name, *params, body=body)

    def is_function(self, name):
        return name in self.functions

    def prep(self):
        """Expose the game's objects and functions to running scripts."""
        self.namespace.update(self.game.objects)
        self.namespace.update(self.functions)

    def export_variables(self):
        """Return the script-level variables (for saving world state)."""
        return {key: value for key, value in self.namespace.items()
                if key not in self.game.objects and key not in self.functions}

    def import_variables(self, variables):
        """Restore script-level variables (when loading world state)."""
        self.namespace.update(variables)

    def reset(self):
        """Forget all fired events and script variables (for a replay)."""
        self.events_fired.clear()
        self.reset_namespace()
        self.prep()

    def run_script(self, script, **kwparams):
        """Run a Script with recursion protection and failure recovery.

        A statement that fails (undefined function, missing object, ...) is
        reported and skipped; neither the rest of the script nor the game
        itself is taken down by it.
        """
        if self._call_depth >= MAX_SCRIPT_DEPTH:
            print("*** Script event loop detected at '{}': maximum nesting "
                  "depth ({}) exceeded, aborting event."
                  .format(script.name, MAX_SCRIPT_DEPTH), file=sys.stderr)
            return None
        self._call_depth += 1
        try:
            return self._execute(script, **kwparams)
        except Exception as ex:  # last-resort safety net
            self._report_error(script, ex)
            return None
        finally:
            self._call_depth -= 1

    def _report_error(self, script, ex):
        print("*** Error in script '{}': {}: {}".format(script.name, type(ex).__name__, ex),
              file=sys.stderr)

    def _execute(self, script, **kwparams):
        # pylint:disable=exec-used,eval-used
        for tag, val in kwparams.items():
            self.namespace[tag] = val
        nodes = self._parse(script)
        return self._exec_nodes(script, nodes)

    def _parse(self, script):
        """Parse the script's lines into a tree of block nodes."""
        lines = script.code.splitlines()
        # Block ids must be deterministic across parses of the same script,
        # otherwise one-shot events (firsttime) re-fire on every call.
        self._block_counter = 0
        nodes, _ = self._parse_block(script, lines, 0, len(lines))
        return nodes

    def _parse_block(self, script, lines, start, end):
        nodes = []
        i = start
        while i < end:
            raw = lines[i]
            words = raw.split()
            if len(words) == 0:
                i += 1
                continue
            if words == ["}"]:
                return nodes, i + 1
            if words[-1] == "{" and len(words) > 1:
                header = ' '.join(words[:-1])
                body, i = self._parse_block(script, lines, i + 1, end)
                if header == "otherwise":
                    nodes.append(("otherwise", body, raw))
                elif header == "firsttime":
                    self._block_counter += 1
                    nodes.append(("firsttime", "block{}".format(self._block_counter), body, raw))
                elif words[0] == "if":
                    branches = [(header[2:].strip(), body)]
                    while i < end:
                        more = lines[i].split()
                        if len(more) > 1 and more[-1] == "{" and \
                                ' '.join(more[:-1]).startswith("else if"):
                            sub, i = self._parse_block(script, lines, i + 1, end)
                            branches.append((' '.join(more[:-1])[8:].strip(), sub))
                        elif len(more) > 1 and more[-1] == "{" and \
                                ' '.join(more[:-1]) == "else":
                            sub, i = self._parse_block(script, lines, i + 1, end)
                            branches.append((None, sub))
                            break
                        else:
                            break
                    nodes.append(("if", branches, raw))
                elif words[0] == "foreach":
                    nodes.append(("foreach", header, body, raw))
                else:
                    nodes.append(("block", header, body, raw))
                continue
            nodes.append(("stmt", raw))
            i += 1
        return nodes, i

    def _exec_nodes(self, script, nodes):
        # pylint:disable=exec-used,eval-used
        i = 0
        while i < len(nodes):
            node = nodes[i]
            try:
                result, consumed = self._exec_node(script, node, nodes, i)
            except Exception as ex:
                # Failure recovery: report the bad statement and move on.
                self._report_error(script, ex)
                result, consumed = _NO_RETURN, 0
            if result is not _NO_RETURN:
                return result
            i += consumed
            i += 1
        return _NO_RETURN

    def _exec_node(self, script, node, nodes, index):
        """Execute one node. Returns (result, extra_nodes_consumed)."""
        kind = node[0]
        if kind == "stmt":
            return self._exec_statement(script, node[1]), 0
        if kind == "block":
            # A bare "{ ... }" block: just run the contents.
            return self._exec_nodes(script, node[2]), 0
        if kind == "if":
            for condition, body in node[1]:
                if condition is None or self._eval_condition(script, condition):
                    return self._exec_nodes(script, body), 0
            return _NO_RETURN, 0
        if kind == "foreach":
            return self._exec_foreach(script, node[1], node[2]), 0
        if kind == "firsttime":
            event_key = script.name + "->" + node[1]
            if event_key in self.events_fired:
                return _NO_RETURN, 0
            self.events_fired.add(event_key)
            result = self._exec_nodes(script, node[2])
            # Consume a directly following "otherwise" block: it only runs
            # when the firsttime block did NOT run.
            consumed = 0
            if index + 1 < len(nodes) and nodes[index + 1][0] == "otherwise":
                consumed = 1
            return result, consumed
        if kind == "otherwise":
            return self._exec_nodes(script, node[1]), 0
        raise SyntaxError("Unknown script node: " + repr(node))

    def _exec_foreach(self, script, header, body):
        words = header.split()
        if len(words) < 3 or not words[1].startswith("(") or "," not in words[1]:
            raise SyntaxError("Malformed foreach header: " + header)
        variable = words[1][1:words[1].index(",")]
        iterable = self._eval_expr(script, ' '.join(words[2:]).rstrip(")"))
        if iterable is None:
            return _NO_RETURN
        for the_val in iterable:
            self.namespace[variable] = the_val
            result = self._exec_nodes(script, body)
            if result is not _NO_RETURN:
                return result
        return _NO_RETURN

    def _eval_condition(self, script, condition):
        words = condition.split()
        for j in range(len(words)):
            if words[j] == "=":
                words[j] = "=="
        return bool(self._eval_expr(script, ' '.join(words)))

    def _eval_expr(self, script, expr):
        return eval(compile(expr, self._where(script), 'eval'), self.namespace)

    def _exec_statement(self, script, line):
        words = line.split()
        if len(words) > 2 and words[0] == "list" and words[1] == "add":
            words[0] = "list_add"
            del words[1]
        if len(words) == 1 and words[0] == "return":
            return None
        if len(words) > 1 and words[0] == "return":
            return self._eval_expr(script, ' '.join(words[1:]))
        exec(compile(' '.join(words), self._where(script), 'exec'), self.namespace)
        return _NO_RETURN

    def _where(self, script):
        return self.game.name + "->" + script.name


class _NoReturn:
    pass


_NO_RETURN = _NoReturn()


class Function:
    def __init__(self, name, *params, body):
        self.name = name
        self.parameters = params
        self.body = body if body is not None else ""

    def __call__(self, *params):
        engine = pyquest.game.the_game.script_engine
        script = Script("functions->" + self.name, self.body)
        return engine.run_script(script, **dict(zip(self.parameters, params)))


class Script:
    def __init__(self, name, code):
        self.name = name
        # An empty script element (<start type="script"></start>) parses as
        # None; treat it as an empty program instead of crashing.
        self.code = code if code is not None else ""

    def __call__(self, **kwparams):
        engine = pyquest.game.the_game.script_engine
        return engine.run_script(self, **kwparams)

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


#
# def print_centered(text):
#     print(text.center(get_terminal_size()[0] - 1))


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
    if not isinstance(text, str):
        text = str(text)
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
        elif isinstance(obj._value, str):
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
