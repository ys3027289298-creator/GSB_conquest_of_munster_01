"""Scripted-input tests for the pyif parser and world state.

Each test feeds a script of commands through the parser (with glk faked
out) and asserts on both the text shown to the player and the resulting
world state.  The state-diff helpers verify that every legal action only
changes the state it is supposed to change.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from harness import make_story, run_script
from pyif import action, message, thing


def snapshot(story):
    """Capture parent + attributes of every object in the world tree."""
    state = {}

    def walk(obj):
        state[obj.name] = (
            obj.parent.name if obj.parent else None,
            frozenset(obj.attributes),
        )
        for child in obj.children:
            walk(child)

    walk(story.root)
    return state


def diff(before, after):
    changed = {}
    for name in before:
        if before[name] != after.get(name):
            changed[name] = (before[name], after.get(name))
    return changed


class ScriptedCase(unittest.TestCase):
    """Runs a fresh story per test; `play` executes one command."""

    def setUp(self):
        self.commands = []
        self.story = None
        self.glk = None
        self.objs = None

    def start(self):
        self.story, self.glk, self.objs = make_story(list(self.commands))
        action.version(self.story)
        action.look(self.story, True)
        self.glk.output.clear()

    def play(self, command):
        """Run one command, returning (output_text, state_diff)."""
        before = snapshot(self.story)
        out_before = len(self.glk.output)
        self.glk.feed(command)
        self.story.parser.read_input()
        text = "".join(self.glk.output[out_before:])
        text = text[len("\n>"):] if text.startswith("\n>") else text
        return text, diff(before, snapshot(self.story))


class TestUnrecognisedVerb(ScriptedCase):
    def test_gibberish_verb_is_rejected_without_state_change(self):
        self.start()
        text, changed = self.play("flibbert")
        self.assertEqual(text, message.NOT_A_VERB)
        self.assertEqual(changed, {})

    def test_uppercase_verb_is_recognised(self):
        self.start()
        text, changed = self.play("TAKE APPLE")
        self.assertIn(message.TAKEN, text)
        self.assertIs(self.objs["apple"].parent, self.story.player)
        self.assertEqual(set(changed), {"red apple"})

    def test_mixed_case_noun_is_recognised(self):
        self.start()
        text, changed = self.play("take APPLE")
        self.assertIn(message.TAKEN, text)
        self.assertIs(self.objs["apple"].parent, self.story.player)


class TestAmbiguousObject(ScriptedCase):
    def test_ambiguous_noun_asks_for_clarification_and_takes_nothing(self):
        self.start()
        text, changed = self.play("take key")
        self.assertIn("Which do you mean", text)
        self.assertIn("brass key", text)
        self.assertIn("iron key", text)
        # Nothing may change while the command is unresolved
        self.assertEqual(changed, {})
        self.assertIs(self.objs["brass_key"].parent, self.objs["hall"])
        self.assertIs(self.objs["iron_key"].parent, self.objs["hall"])

    def test_disambiguating_adjective_picks_the_right_object(self):
        self.start()
        text, changed = self.play("take brass")
        self.assertIn(message.TAKEN, text)
        self.assertIs(self.objs["brass_key"].parent, self.story.player)
        self.assertIs(self.objs["iron_key"].parent, self.objs["hall"])
        self.assertEqual(set(changed), {"brass key"})


class TestEmptyRoom(ScriptedCase):
    def test_lit_empty_room_without_description_does_not_crash(self):
        self.start()
        bare = thing.Room("Bare Room", self.story.root)
        bare.nouns = ["bare"]
        bare.attributes.add(thing.LIGHT)
        self.objs["hall"].e_to = bare
        text, changed = self.play("e")
        self.assertIn("Bare Room", text)
        self.assertIs(self.story.player.room(), bare)

    def test_dark_empty_room_reports_darkness(self):
        self.start()
        dark = thing.Room("Dark Room", self.story.root)
        dark.nouns = ["dark"]
        dark.description = "A dark room."
        self.objs["hall"].e_to = dark
        text, changed = self.play("e")
        self.assertIn(message.DARKNESS, text)
        self.assertIn(message.DARKNESS_DESC, text)

    def test_empty_room_has_no_visible_contents(self):
        self.start()
        text, changed = self.play("s")  # cellar is lit and empty
        self.assertIn("Cellar", text)
        self.assertNotIn(message.CAN_SEE.split("%s")[0], text)
        self.assertIs(self.story.player.room(), self.objs["cellar"])

    def test_blocked_exit_from_empty_room_changes_nothing(self):
        self.start()
        self.play("s")
        text, changed = self.play("n")  # cellar has no north exit
        self.assertEqual(text, message.CANT_GO)
        self.assertIs(self.story.player.room(), self.objs["cellar"])
        self.assertEqual(changed, {})


class TestRepeatedTake(ScriptedCase):
    def test_second_take_reports_already_held(self):
        self.start()
        self.play("take apple")
        text, changed = self.play("take apple")
        self.assertEqual(text, message.ALREADY_HAVE)
        self.assertEqual(changed, {})

    def test_repeated_take_does_not_duplicate_inventory(self):
        self.start()
        self.play("take apple")
        self.play("take apple")
        self.play("take apple")
        apples = [c for c in self.story.player.children if c.name == "red apple"]
        self.assertEqual(len(apples), 1)


class TestActionResultPersistence(ScriptedCase):
    def test_taken_item_can_be_dropped(self):
        self.start()
        self.play("take apple")
        text, changed = self.play("drop apple")
        self.assertEqual(text, message.DROPPED)
        self.assertIs(self.objs["apple"].parent, self.objs["hall"])
        self.assertEqual(set(changed), {"red apple"})

    def test_implicit_take_for_held_verbs(self):
        self.start()
        text, changed = self.play("eat apple")
        self.assertIn(message.FIRST_TAKING.split("%s")[0], text)
        self.assertIs(self.objs["apple"].parent, self.story.player)

    def test_implicit_take_preserves_the_pending_action(self):
        self.start()
        self.play("eat apple")
        # The implicit take must not clobber the real action/nouns
        self.assertIs(self.story.action, action.eat)
        self.assertEqual(self.story.nouns, [self.objs["apple"]])

    def test_failed_command_leaves_no_stale_action(self):
        self.start()
        self.play("take apple")
        self.play("flibbert")
        self.assertIsNone(self.story.action)
        self.assertEqual(self.story.nouns, [])

    def test_worn_state_survives_drop_via_disrobe(self):
        self.start()
        text, changed = self.play("drop cloak")
        self.assertIn(message.FIRST_TAKING_OFF.split("%s")[0], text)
        self.assertIn(message.DROPPED, text)
        self.assertNotIn(thing.WORN, self.objs["cloak"].attributes)
        self.assertIs(self.objs["cloak"].parent, self.objs["hall"])


class TestDebugLeak(ScriptedCase):
    def test_normal_play_produces_no_log_output(self):
        self.start()
        for command in ["look", "take apple", "drop apple", "s", "n", "i"]:
            text, _ = self.play(command)
            self.assertNotIn("[LOG]", text, "log leaked for %r" % command)

    def test_debug_verbs_are_not_part_of_normal_grammar(self):
        self.start()
        for command in ["actions", "messages", "tree", "grammar"]:
            text, changed = self.play(command)
            self.assertEqual(text, message.NOT_A_VERB)
            self.assertEqual(changed, {})


class TestHeldTokenActions(ScriptedCase):
    """Verbs whose grammar uses HELD_TOKEN must match and run."""

    def test_wear_non_clothing_is_refused(self):
        self.start()
        text, changed = self.play("wear apple")
        self.assertIn(message.CANT_WEAR, text)

    def test_wear_clothing_marks_it_worn(self):
        self.start()
        self.play("take off cloak")
        text, changed = self.play("wear cloak")
        self.assertEqual(text, message.WORN % "black cloak")
        self.assertIn(thing.WORN, self.objs["cloak"].attributes)
        self.assertEqual(set(changed), {"black cloak"})

    def test_put_on_supporter(self):
        self.start()
        table = thing.Thing("oak table", self.objs["hall"])
        table.nouns = ["oak", "table"]
        table.attributes.add(thing.SUPPORTER)
        self.play("take apple")
        text, changed = self.play("put apple on table")
        self.assertEqual(text, message.PUT_ON % ("red apple", "oak table"))
        self.assertIs(self.objs["apple"].parent, table)

    def test_examine_callable_description(self):
        self.start()
        called = []

        def describe(self):
            called.append(True)

        self.objs["apple"].description = describe
        text, changed = self.play("x apple")
        self.assertEqual(called, [True])
        self.assertEqual(changed, {})


class TestMovementState(ScriptedCase):
    def test_go_only_moves_the_player(self):
        self.start()
        text, changed = self.play("s")
        self.assertIs(self.story.player.room(), self.objs["cellar"])
        # player parent changes; the cellar gains VISITED via implicit look
        self.assertEqual(set(changed), {"cretin", "Cellar"})

    def test_look_marks_room_visited_only(self):
        self.start()
        self.objs["hall"].attributes.discard(thing.VISITED)
        text, changed = self.play("look")
        self.assertEqual(set(changed), {"Hall"})
        self.assertIn(thing.VISITED, self.objs["hall"].attributes)


if __name__ == "__main__":
    unittest.main()
