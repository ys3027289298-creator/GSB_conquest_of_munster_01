"""Scripted-input regression tests for the pyif parser and world state.

Each test drives the parser with a scripted command list through a fake
glk layer (no curses) and asserts both the emitted text and the exact
world-state delta, so a legal action may only change the state it owns.
"""

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyif import glk, thing, message, debug
from pyif.thing import Thing, Room
from pyif.story import Story


class ScriptedGlk:
    "In-memory replacement for the curses glk layer."

    def __init__(self, commands):
        self.commands = list(commands)
        self.output = io.StringIO()

    def get_string(self):
        if not self.commands:
            raise AssertionError("script ran out of commands")
        return self.commands.pop(0)

    def put_string(self, s):
        self.output.write(s)

    def put_char(self, c):
        self.output.write(c)

    def set_style(self, style):
        pass


def play(story, commands):
    "Run the parser over scripted commands and return the game output."
    scripted = ScriptedGlk(list(commands) + ["quit"])
    glk.get_string = scripted.get_string
    glk.put_string = scripted.put_string
    glk.put_char = scripted.put_char
    glk.set_style = scripted.set_style
    while story.parser.read_input():
        pass
    return scripted.output.getvalue()


def snapshot(story):
    "A comparable view of the whole world: name -> (parent, attributes)."
    state = {}

    def walk(obj):
        state[obj.name] = (
            obj.parent.name if obj.parent is not None else None,
            frozenset(obj.attributes),
        )
        for child in obj.children:
            walk(child)

    walk(story.root)
    return state


def diff(before, after):
    "Names whose (parent, attributes) changed between two snapshots."
    return {name for name in before if before[name] != after[name]}


def build_story():
    story = Story("Test Story", "a test world", None)

    hall = Room("Hall", story.root)
    hall.nouns = ["hall"]
    hall.description = "The hall."
    hall.attributes.add(thing.LIGHT)

    cave = Room("Cave", story.root)
    cave.nouns = ["cave"]
    cave.description = "The cave."
    cave.attributes.add(thing.LIGHT)

    hall.n_to = cave
    cave.s_to = hall

    # A room with no exits at all
    empty = Room("Empty", story.root)
    empty.nouns = ["empty"]
    empty.description = "Nothing here."
    empty.attributes.add(thing.LIGHT)
    hall.e_to = empty

    thing.move(story.player, hall)

    ball = Thing("red ball", hall)
    ball.nouns = ["red", "ball"]
    ball.description = "A red ball."

    box = Thing("red box", hall)
    box.nouns = ["red", "box"]
    box.description = "A red box."

    cloak = Thing("velvet cloak", hall)
    cloak.nouns = ["velvet", "cloak"]
    cloak.attributes.add(thing.CLOTHING)
    cloak.description = lambda self: glk.put_string("A velvet cloak.\n")

    return story, hall, cave, empty, ball, box, cloak


class ParserTest(unittest.TestCase):

    def setUp(self):
        debug.set_enabled(False)
        self.story, self.hall, self.cave, self.empty, \
            self.ball, self.box, self.cloak = build_story()

    def test_unrecognised_verb_changes_nothing(self):
        before = snapshot(self.story)
        out = play(self.story, ["xyzzy"])
        self.assertIn(message.NOT_A_VERB, out)
        self.assertEqual(before, snapshot(self.story))

    def test_unrecognised_noun_changes_nothing(self):
        before = snapshot(self.story)
        out = play(self.story, ["take balloon"])
        self.assertIn(message.UNDERSTAND_AS_FAR % "take", out)
        self.assertEqual(before, snapshot(self.story))

    def test_held_token_verb_is_recognised(self):
        # 'wear' takes a HELD_TOKEN; the cloak is in the room, so the
        # parser performs an implicit take and then wears it.
        out = play(self.story, ["wear cloak"])
        self.assertNotIn(message.UNDERSTAND_AS_FAR % "wear", out)
        self.assertIn(message.FIRST_TAKING % ("a", "velvet cloak"), out)
        self.assertIn(message.WORN % "velvet cloak", out)
        self.assertIs(self.cloak.parent, self.story.player)
        self.assertIn(thing.WORN, self.cloak.attributes)

    def test_implicit_take_of_held_item_is_not_repeated(self):
        # Once held, 'wear cloak' must not take it again.
        play(self.story, ["take cloak"])
        out = play(self.story, ["wear cloak"])
        self.assertNotIn(message.FIRST_TAKING % ("a", "velvet cloak"), out)

    def test_ambiguous_noun_is_questioned_and_changes_nothing(self):
        before = snapshot(self.story)
        out = play(self.story, ["take red"])
        self.assertIn(message.WHICH_ONE % "a red ball or a red box", out)
        self.assertEqual(before, snapshot(self.story))

    def test_ambiguous_noun_can_be_resolved_by_rephrasing(self):
        play(self.story, ["take red"])
        out = play(self.story, ["take ball"])
        self.assertIn(message.TAKEN, out)
        self.assertIs(self.ball.parent, self.story.player)
        self.assertIs(self.box.parent, self.hall)

    def test_empty_room_without_exits(self):
        out = play(self.story, ["e", "n", "s", "w"])
        self.assertIn("Empty", out)
        self.assertEqual(out.count(message.CANT_GO), 3)
        self.assertIs(self.story.player.room(), self.empty)

    def test_roomless_actor_does_not_crash(self):
        story = Story("Nowhere", "no rooms", None)  # player never placed
        self.assertIsNone(story.player.room())
        out = play(story, ["n", "look"])
        self.assertIn(message.CANT_GO, out)

    def test_room_module_exports_real_room(self):
        from pyif.room import Room as ExportedRoom
        self.assertIs(ExportedRoom, thing.Room)

    def test_repeated_take_reports_and_changes_nothing(self):
        calls = []

        def ball_after(obj, story):
            calls.append(story.action)
            return False

        self.ball.after = ball_after
        out = play(self.story, ["take ball", "take ball"])
        self.assertEqual(out.count(message.TAKEN), 1)
        self.assertIn(message.ALREADY_HAVE, out)
        self.assertEqual(len(calls), 1, "after hooks must fire exactly once")
        self.assertIs(self.ball.parent, self.story.player)

    def test_verbose_mode_persists_across_turns(self):
        out = play(self.story, ["verbose", "n", "s", "n"])
        self.assertEqual(self.story.mode, "verbose")
        # Cave description prints on both visits under verbose
        self.assertEqual(out.count("The cave."), 2)

    def test_brief_mode_suppresses_visited_descriptions(self):
        out = play(self.story, ["n", "s", "n"])
        self.assertEqual(self.story.mode, "brief")
        self.assertEqual(out.count("The cave."), 1)

    def test_superbrief_mode_suppresses_all_implicit_descriptions(self):
        out = play(self.story, ["superbrief", "n"])
        self.assertEqual(self.story.mode, "superbrief")
        self.assertNotIn("The cave.", out)

    def test_explicit_look_always_describes(self):
        out = play(self.story, ["superbrief", "n", "look"])
        self.assertIn("The cave.", out)

    def test_no_debug_output_in_release_flow(self):
        out = play(self.story, ["take ball", "drop ball", "look", "n", "s"])
        self.assertNotIn("[LOG]", out)

    def test_debug_verbs_not_in_release_grammar(self):
        for token in ("tree", "dump", "actions", "grammar", "messages"):
            self.assertIsNone(self.story.grammar.find_verb_matching_token(token))
        out = play(self.story, ["tree"])
        self.assertIn(message.NOT_A_VERB, out)

    def test_debug_verbs_available_when_debug_enabled(self):
        debug.set_enabled(True)
        try:
            story, _, _, _, _, _, _ = build_story()
            self.assertIsNotNone(story.grammar.find_verb_matching_token("tree"))
            out = play(story, ["take ball"])
            self.assertIn("[LOG]", out)
        finally:
            debug.set_enabled(False)


class WorldStateTest(unittest.TestCase):
    "Every legal action may only change the state it is responsible for."

    def setUp(self):
        debug.set_enabled(False)
        self.story, self.hall, self.cave, self.empty, \
            self.ball, self.box, self.cloak = build_story()

    def test_examine_changes_nothing(self):
        before = snapshot(self.story)
        out = play(self.story, ["examine ball"])
        self.assertIn("A red ball.", out)
        self.assertEqual(diff(before, snapshot(self.story)), set())

    def test_examine_callable_description(self):
        before = snapshot(self.story)
        out = play(self.story, ["examine cloak"])
        self.assertIn("A velvet cloak.", out)
        self.assertEqual(diff(before, snapshot(self.story)), set())

    def test_take_only_moves_the_taken_item(self):
        before = snapshot(self.story)
        play(self.story, ["take ball"])
        self.assertEqual(diff(before, snapshot(self.story)), {"red ball"})

    def test_failed_second_take_changes_nothing_more(self):
        play(self.story, ["take ball"])
        before = snapshot(self.story)
        play(self.story, ["take ball"])
        self.assertEqual(diff(before, snapshot(self.story)), set())

    def test_drop_only_moves_the_dropped_item(self):
        play(self.story, ["take ball"])
        before = snapshot(self.story)
        play(self.story, ["drop ball"])
        self.assertEqual(diff(before, snapshot(self.story)), {"red ball"})
        self.assertIs(self.ball.parent, self.hall)

    def test_wear_only_touches_the_garment(self):
        before = snapshot(self.story)
        play(self.story, ["wear cloak"])
        self.assertEqual(diff(before, snapshot(self.story)), {"velvet cloak"})

    def test_movement_only_moves_the_player_and_marks_visited(self):
        before = snapshot(self.story)
        play(self.story, ["n"])
        self.assertEqual(
            diff(before, snapshot(self.story)), {"cretin", "Cave"})
        self.assertIs(self.story.player.room(), self.cave)
        self.assertIn(thing.VISITED, self.cave.attributes)

    def test_failed_movement_changes_nothing(self):
        before = snapshot(self.story)
        play(self.story, ["s"])  # no exit south of the hall
        self.assertEqual(diff(before, snapshot(self.story)), set())

    def test_inventory_changes_nothing(self):
        play(self.story, ["take ball"])
        before = snapshot(self.story)
        out = play(self.story, ["inventory"])
        self.assertIn("red ball", out)
        self.assertEqual(diff(before, snapshot(self.story)), set())


if __name__ == "__main__":
    unittest.main()
