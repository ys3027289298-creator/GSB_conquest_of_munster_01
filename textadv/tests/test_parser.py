"""Tests for textadv.gamesystem.parser: understand/handle_all, error
reporting, and disambiguation."""

import unittest

from tests import *  # noqa: F401,F403  (sets up sys.path)

from textadv.gamesystem import parser as parser_mod
from textadv.gamesystem.parser import (Parser, default_parser, default_parse_text,
                                       NoSuchWord, NoUnderstand, NoInput, Ambiguous)
from textadv.gamesystem.actionsystem import BasicAction, LogicalOperation, IllogicalOperation
from textadv.gamesystem.basicpatterns import X, actor
from textadv.gamesystem.utilities import stringeval, list_append
from textadv.gamesystem.world import World, Property


class Examining(BasicAction) :
    verb = "examine"
    gerund = "examining"
    numargs = 2
class Taking(BasicAction) :
    verb = "take"
    gerund = "taking"
    numargs = 2


class FakeContext(object) :
    def __init__(self, world, actor="player") :
        self.world = world
        self.actor = actor
        self.stringeval = stringeval


def make_world(objects=()) :
    """A world with just enough for the parser: Name/Words properties
    and an objects_of_kind activity.  objects is a list of (id, name)
    pairs."""
    world = World()

    @world.define_property
    class Name(Property) :
        numargs = 1

    @world.define_property
    class Words(Property) :
        numargs = 1

    world.define_activity("objects_of_kind", accumulator=list_append)

    @world.to("objects_of_kind")
    def _objects_of_kind(kind, world) :
        if kind == "thing" :
            return [o for o, name in objects]
        return []

    for o, name in objects :
        world[Name(o)] = name
        words = name.split()
        words[-1] = "@" + words[-1]
        world[Words(o)] = words

    return world


def verify_all(action, ctxt) :
    return LogicalOperation()


def make_parser() :
    """A fresh parser with the default thing/text parsing machinery,
    but no grammar rules of its own."""
    parser = Parser()
    parser.parse_thing = default_parser.parse_thing.copy()
    parser.define_subparser("action")
    parser.define_subparser("something")
    parser.define_subparser("text")
    parser.object_classes = {"something" : "thing"}

    @parser.add_subparser("something")
    def _something(parser, var, input, i, ctxt, actor, next) :
        return list_append([parser.parse_thing.notify([parser, "something", var, name, words, input, i, ctxt, next], {})
                            for name, words in zip(parser.current_objects["something"],
                                                   parser.current_words["something"])])

    @parser.add_subparser("text")
    def _text(parser, var, input, i, ctxt, actor, next) :
        return default_parse_text(parser, var, input, i, ctxt, actor, next)

    return parser


class TestHandleAll(unittest.TestCase) :
    def setUp(self) :
        self.parser = make_parser()

    def test_simple_action(self) :
        world = make_world([("red ball", "red ball")])
        self.parser.understand("examine [something x]", Examining(actor, X))
        action, disambiguated = self.parser.handle_all("examine the red ball",
                                                       FakeContext(world), verify_all)
        self.assertEqual(action, Examining("player", "red ball"))

    def test_no_input(self) :
        world = make_world()
        self.parser.understand("examine [something x]", Examining(actor, X))
        self.assertRaises(NoInput, self.parser.handle_all, "   ",
                          FakeContext(world), verify_all)

    def test_no_such_word(self) :
        world = make_world([("red ball", "red ball")])
        self.parser.understand("examine [something x]", Examining(actor, X))
        try :
            self.parser.handle_all("examine the frobnicate", FakeContext(world), verify_all)
            self.fail("expected NoSuchWord")
        except NoSuchWord as ex :
            self.assertEqual(ex.word, "frobnicate")

    def test_no_understand(self) :
        world = make_world([("red ball", "red ball")])
        self.parser.understand("examine [something x]", Examining(actor, X))
        # "ball" is a known word, but "ball examine" parses as nothing
        self.assertRaises(NoUnderstand, self.parser.handle_all, "ball examine",
                          FakeContext(world), verify_all)

    def test_period_at_end(self) :
        world = make_world([("red ball", "red ball")])
        self.parser.understand("examine [something x]", Examining(actor, X))
        action, _ = self.parser.handle_all("examine ball.", FakeContext(world),
                                           verify_all, allow_period_at_end=True)
        self.assertEqual(action, Examining("player", "red ball"))

    def test_slash_word_options(self) :
        world = make_world([("red ball", "red ball")])
        self.parser.understand("examine/x/inspect [something x]", Examining(actor, X))
        for command in ["examine ball", "x ball", "inspect ball"] :
            action, _ = self.parser.handle_all(command, FakeContext(world), verify_all)
            self.assertEqual(action, Examining("player", "red ball"))

    def test_transform_text_to_words(self) :
        self.assertEqual(self.parser.transform_text_to_words("take ball, then drop it"),
                         ["take", "ball", ",", "then", "drop", "it"])


class TestDisambiguation(unittest.TestCase) :
    def setUp(self) :
        self.parser = make_parser()

    def test_genuine_ambiguity_raises(self) :
        """Two objects matching the same noun must raise Ambiguous
        with both objects as options."""
        world = make_world([("red ball", "red ball"), ("blue ball", "blue ball")])
        self.parser.understand("examine [something x]", Examining(actor, X))
        try :
            self.parser.handle_all("examine ball", FakeContext(world), verify_all)
            self.fail("expected Ambiguous")
        except Ambiguous as ex :
            options = sorted(ex.options.values())[0]
            self.assertEqual(sorted(options), ["blue ball", "red ball"])

    def test_adjective_disambiguates(self) :
        world = make_world([("red ball", "red ball"), ("blue ball", "blue ball")])
        self.parser.understand("examine [something x]", Examining(actor, X))
        action, _ = self.parser.handle_all("examine blue ball", FakeContext(world), verify_all)
        self.assertEqual(action, Examining("player", "blue ball"))

    def test_identical_results_are_not_ambiguous(self) :
        """If two parse paths produce the *same* action (for instance
        when a grammar rule was registered twice), the result is not
        ambiguous."""
        world = make_world([("red ball", "red ball")])
        self.parser.understand("examine [something x]", Examining(actor, X))
        # simulate a game module being loaded twice:
        self.parser.understand("examine [something x]", Examining(actor, X))
        action, _ = self.parser.handle_all("examine ball", FakeContext(world), verify_all)
        self.assertEqual(action, Examining("player", "red ball"))

    def test_text_parser(self) :
        """[text x] consumes the rest of the input as a string."""
        world = make_world()
        self.parser.understand("say [text t]", lambda t, actor : ("say", t))
        action, _ = self.parser.handle_all("say hello world", FakeContext(world), verify_all)
        self.assertEqual(action, ("say", "hello world"))

    def test_verification_score_disambiguates(self) :
        """A more logical action wins over a less logical one without
        asking the user."""
        world = make_world([("red ball", "red ball"), ("blue ball", "blue ball")])
        self.parser.understand("take [something x]", Taking(actor, X))

        def verify(action, ctxt) :
            if action.get_do() == "red ball" :
                return IllogicalOperation("It's too hot.")
            return LogicalOperation()

        action, disambiguated = self.parser.handle_all("take ball", FakeContext(world), verify)
        self.assertEqual(action, Taking("player", "blue ball"))
        # only one acceptable option, so no user disambiguation needed
        self.assertFalse(disambiguated)


if __name__ == "__main__" :
    unittest.main()
