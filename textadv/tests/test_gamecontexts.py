"""Tests for textadv.gamesystem.gamecontexts (ActorContext and
friends)."""

import unittest

from tests import *  # noqa: F401,F403  (sets up sys.path)

from textadv.gamesystem.actionsystem import ActionSystem
from textadv.gamesystem.gamecontexts import ActorContext, ActorActivities
from textadv.gamesystem.parser import Parser
from textadv.gamesystem.utilities import stringeval
from textadv.gamesystem.world import World


class NullIO(object) :
    def get_input(self, prompt=">") :
        raise SystemExit(0)
    def write(self, *data) :
        pass
    def set_status_var(self, *args, **kwargs) :
        pass
    def flush(self) :
        pass


def make_actor_context() :
    actoractivities = ActorActivities()
    actoractivities.define_activity("step_turn")
    return ActorContext(None, NullIO(), World(), ActionSystem(), Parser(),
                        stringeval, actoractivities, "player")


class TestActorContext(unittest.TestCase) :
    def test_activity_table_uses_context_actoractivities(self) :
        """ActorContext.activity_table must look the activity up in
        the context's own actoractivities (regression: it referenced a
        commented-out module global and raised NameError)."""
        ctxt = make_actor_context()
        table = ctxt.activity_table("step_turn")
        self.assertIs(table, ctxt.actoractivities.activity_table("step_turn"))

    def test_call_activity(self) :
        ctxt = make_actor_context()
        calls = []

        @ctxt.actoractivities.to("step_turn")
        def _step(ctxt) :
            calls.append("stepped")

        ctxt.call_activity("step_turn")
        self.assertEqual(calls, ["stepped"])

    def test_write_evaluates_strings(self) :
        ctxt = make_actor_context()
        collected = []
        ctxt.io.write = lambda *data : collected.extend(data)
        ctxt.write("plain text and [char 65]BC")
        self.assertEqual(collected, ["plain text and ABC"])


if __name__ == "__main__" :
    unittest.main()
