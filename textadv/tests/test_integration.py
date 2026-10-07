"""End-to-end tests driving the full library (parser -> action system
-> world) through an ActorContext with a scripted terminal-like IO.

The game is built out of the standard rule library; this file defines
no rules of its own."""

import unittest

from tests import *  # noqa: F401,F403  (sets up sys.path)

import textadv.basicsetup as bl
from textadv.basicsetup import *
from textadv.gamesystem.gamecontexts import execute_context


bl.world[Global("game_title")] = "Integration"
bl.world[Global("game_author")] = "tests"

quickdef(bl.world, "Kitchen", "room",
         {Description : "A small kitchen."})
quickdef(bl.world, "Hall", "room",
         {Description : "A long hall."})
bl.world.activity.connect_rooms("Kitchen", "north", "Hall")

quickdef(bl.world, "red ball", "thing",
         {Description : "A shiny red ball."},
         put_in="Kitchen")
quickdef(bl.world, "blue ball", "thing",
         {Description : "A dull blue ball."},
         put_in="Kitchen")
bl.world.activity.put_in("player", "Kitchen")


class ScriptIO(object) :
    def __init__(self, inputs) :
        self.inputs = list(inputs)
        self.data = []
    def get_input(self, prompt=">") :
        if not self.inputs :
            raise SystemExit(0)
        return self.inputs.pop(0)
    def write(self, *data) :
        self.data.extend(data)
    def set_status_var(self, *args, **kwargs) :
        pass
    def flush(self) :
        pass


def play(*inputs) :
    io = ScriptIO(inputs)
    ctxt = bl.make_actorcontext_with_io(io)
    ctxt.world.set_game_defined()
    try :
        execute_context(ctxt)
    except SystemExit :
        pass
    return ctxt, io


def text_of(io) :
    return "\n".join(str(o) for o in io.data)


class TestPlayCommands(unittest.TestCase) :
    def test_take_writes_back_to_world(self) :
        ctxt, io = play("take red ball", "quit-nope")
        held = ctxt.world.query_relation(bl.Has("player", X), var=X)
        self.assertIn("red ball", held)
        self.assertIn("Taken", text_of(io))

    def test_inventory_lists_carried(self) :
        ctxt, io = play("take blue ball", "inventory")
        out = text_of(io)
        self.assertIn("blue ball", out)
        self.assertIn("carrying", out)

    def test_drop(self) :
        ctxt, io = play("take red ball", "drop red ball")
        held = ctxt.world.query_relation(bl.Has("player", X), var=X)
        self.assertNotIn("red ball", held)
        self.assertIn("Dropped", text_of(io))

    def test_go_changes_location(self) :
        ctxt, io = play("go north")
        self.assertEqual(ctxt.world.get_property("Location", "player"), "Hall")
        self.assertIn("A long hall", text_of(io))
        # the ball stayed in the kitchen
        self.assertEqual(ctxt.world.get_property("Location", "red ball"), "Kitchen")

    def test_examine(self) :
        ctxt, io = play("x red ball")
        self.assertIn("A shiny red ball", text_of(io))

    def test_unknown_word(self) :
        ctxt, io = play("frobnicate the red ball")
        self.assertIn("I don't know what you mean by 'frobnicate'", text_of(io))

    def test_period(self) :
        ctxt, io = play("x red ball.")
        self.assertIn("A shiny red ball", text_of(io))

    def test_ambiguous_then_disambiguate(self) :
        ctxt, io = play("take ball", "blue ball")
        held = ctxt.world.query_relation(bl.Has("player", X), var=X)
        self.assertIn("blue ball", held)
        self.assertNotIn("red ball", held)
        self.assertIn("Did you mean", text_of(io))

    def test_serialize_roundtrip_then_play(self) :
        """State saved after a move and a take must restore correctly,
        and further commands must act on the restored world."""
        ctxt, io = play("take red ball", "go north")
        data = ctxt.world.serialize()
        restored = ctxt.world.deserialize(data)
        self.assertEqual(restored.get_property("Location", "player"), "Hall")
        self.assertIn("red ball", restored.query_relation(bl.Has("player", X), var=X))
        # an activity on the restored world acts on the restored world
        restored.activity.put_in("blue ball", "Hall")
        self.assertEqual(restored.get_property("Location", "blue ball"), "Hall")
        self.assertEqual(ctxt.world.get_property("Location", "blue ball"), "Kitchen")


if __name__ == "__main__" :
    unittest.main()
