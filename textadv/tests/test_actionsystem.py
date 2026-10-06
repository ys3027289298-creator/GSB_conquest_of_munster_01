"""Tests for textadv.gamesystem.actionsystem: the verify/trybefore/
before/when/report pipeline, DoInstead redirection, and that action
effects are written back to the world."""

import unittest

from tests import *  # noqa: F401,F403  (sets up sys.path)

from textadv.core.rulesystem import AbortAction, ActionHandled
from textadv.gamesystem.actionsystem import (ActionSystem, BasicAction,
                                             DoInstead, LogicalOperation,
                                             IllogicalOperation, VeryLogicalOperation,
                                             verify_instead)
from textadv.gamesystem.basicpatterns import X, actor
from textadv.gamesystem.world import World, Property


class Taking(BasicAction) :
    verb = "take"
    gerund = "taking"
    numargs = 2
class Dropping(BasicAction) :
    verb = "drop"
    gerund = "dropping"
    numargs = 2


class FakeContext(object) :
    """A minimal context: enough for ActionSystem.run_action."""
    def __init__(self, world, actionsystem) :
        self.world = world
        self.actionsystem = actionsystem
        self.actor = "player"
        self.written = []
    def write(self, *stuff, **kwargs) :
        self.written.extend(stuff)


def make_world() :
    world = World()

    @world.define_property
    class Carrying(Property) :
        numargs = 2

    world[Carrying("player", "ball")] = False
    return world


class TestRunAction(unittest.TestCase) :
    def setUp(self) :
        self.actionsystem = ActionSystem()
        self.world = make_world()
        self.ctxt = FakeContext(self.world, self.actionsystem)

    def test_when_result_written_back_to_world(self) :
        """Effects of the when-handler must be visible in the world
        afterwards (the action's results are written back to the
        world)."""
        Carrying = self.world.property_types["Carrying"]

        @self.actionsystem.when(Taking(actor, X))
        def do_take(actor, x, ctxt) :
            ctxt.world[Carrying("player", x)] = True

        self.actionsystem.run_action(Taking("player", "ball"), self.ctxt)
        self.assertTrue(self.world[Carrying("player", "ball")])

    def test_report_runs_after_when(self) :
        order = []

        @self.actionsystem.when(Taking(actor, X))
        def do_take(actor, x, ctxt) :
            order.append("when")

        @self.actionsystem.report(Taking(actor, X))
        def report_take(actor, x, ctxt) :
            order.append("report")

        self.actionsystem.run_action(Taking("player", "ball"), self.ctxt)
        self.assertEqual(order, ["when", "report"])

    def test_report_skipped_when_silently(self) :
        order = []

        @self.actionsystem.when(Taking(actor, X))
        def do_take(actor, x, ctxt) :
            order.append("when")

        @self.actionsystem.report(Taking(actor, X))
        def report_take(actor, x, ctxt) :
            order.append("report")

        self.actionsystem.run_action(Taking("player", "ball"), self.ctxt, silently=True)
        self.assertEqual(order, ["when"])

    def test_illogical_action_aborts(self) :
        calls = []

        @self.actionsystem.verify(Taking(actor, X))
        def verify_take(actor, x, ctxt) :
            return IllogicalOperation("You can't take that.")

        @self.actionsystem.when(Taking(actor, X))
        def do_take(actor, x, ctxt) :
            calls.append("when")

        self.assertRaises(AbortAction, self.actionsystem.run_action,
                          Taking("player", "ball"), self.ctxt)
        self.assertEqual(calls, [])
        self.assertIn("You can't take that.", self.ctxt.written)

    def test_before_can_abort(self) :
        calls = []

        @self.actionsystem.before(Taking(actor, X))
        def before_take(actor, x, ctxt) :
            raise AbortAction("It is nailed down.")

        @self.actionsystem.when(Taking(actor, X))
        def do_take(actor, x, ctxt) :
            calls.append("when")

        self.assertRaises(AbortAction, self.actionsystem.run_action,
                          Taking("player", "ball"), self.ctxt)
        self.assertEqual(calls, [])

    def test_do_instead_redirects(self) :
        calls = []

        @self.actionsystem.before(Taking(actor, X))
        def before_take(actor, x, ctxt) :
            raise DoInstead(Dropping(actor, x), suppress_message=True)

        @self.actionsystem.when(Taking(actor, X))
        def do_take(actor, x, ctxt) :
            calls.append("take")

        @self.actionsystem.when(Dropping(actor, X))
        def do_drop(actor, x, ctxt) :
            calls.append("drop")

        self.actionsystem.run_action(Taking("player", "ball"), self.ctxt)
        self.assertEqual(calls, ["drop"])

    def test_verify_action_scoring(self) :
        @self.actionsystem.verify(Taking(actor, X))
        def verify_take(actor, x, ctxt) :
            return VeryLogicalOperation()

        result = self.actionsystem.verify_action(Taking("player", "ball"), self.ctxt)
        self.assertTrue(result.is_acceptible())
        self.assertEqual(result.score, 150)

    def test_verify_action_default_logical(self) :
        result = self.actionsystem.verify_action(Taking("player", "ball"), self.ctxt)
        self.assertTrue(result.is_acceptible())

    def test_verify_instead(self) :
        """verify_instead raises ActionHandled carrying the
        verification of the other action (regression: it referenced
        unimported ActionHandled and an undefined global
        verify_action)."""
        @self.actionsystem.verify(Dropping(actor, X))
        def verify_drop(actor, x, ctxt) :
            return IllogicalOperation("No dropping.")

        @self.actionsystem.verify(Taking(actor, X))
        def verify_take(actor, x, ctxt) :
            verify_instead(Dropping(actor, x), ctxt)

        result = self.actionsystem.verify_action(Taking("player", "ball"), self.ctxt)
        self.assertFalse(result.is_acceptible())
        self.assertEqual(result.reason, "No dropping.")

    def test_copy_isolation(self) :
        @self.actionsystem.when(Taking(actor, X))
        def do_take(actor, x, ctxt) :
            ctxt.world[ctxt.world.property_types["Carrying"]("player", x)] = True

        copied = self.actionsystem.copy()
        calls = []

        @copied.when(Taking(actor, X))
        def extra(actor, x, ctxt) :
            calls.append("extra")

        self.actionsystem.run_action(Taking("player", "ball"), self.ctxt)
        self.assertEqual(calls, [])


if __name__ == "__main__" :
    unittest.main()
