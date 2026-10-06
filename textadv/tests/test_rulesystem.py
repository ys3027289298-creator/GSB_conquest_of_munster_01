"""Tests for textadv.core.rulesystem (RuleTable, ActivityTable,
PropertyTable) and textadv.core.patterns."""

import unittest

from tests import *  # noqa: F401,F403  (sets up sys.path)

from textadv.core.patterns import (BasicPattern, VarPattern, NoMatchException,
                                   DuplicateVariableException)
from textadv.core.rulesystem import (RuleTable, ActivityTable, PropertyTable,
                                     NotHandled, AbortAction, ActionHandled,
                                     MultipleResults, FinishWith, RestartWith,
                                     make_rule_decorator)


class PEnters(BasicPattern) :
    def __init__(self, actor, place) :
        self.args = [actor, place]
class PBefore(BasicPattern) :
    def __init__(self, event) :
        self.args = [event]
class PAfter(BasicPattern) :
    def __init__(self, event) :
        self.args = [event]

X = VarPattern("x")


class TestPatterns(unittest.TestCase) :
    def test_var_match(self) :
        self.assertEqual(VarPattern("v").match("hi"), {"v" : "hi"})

    def test_duplicate_var(self) :
        pattern = BasicPattern(VarPattern("x"), VarPattern("x"))
        self.assertRaises(DuplicateVariableException,
                          pattern.match, BasicPattern(1, 2))

    def test_basic_pattern_subclasses(self) :
        pattern = PEnters("kyle", X)
        self.assertEqual(pattern.match(PEnters("kyle", "vestibule")),
                         {"x" : "vestibule"})
        self.assertRaises(NoMatchException, pattern.match,
                          PEnters("bob", "vestibule"))

    def test_expand(self) :
        p = PEnters("kyle", X)
        self.assertEqual(p.expand_pattern({"x" : "hall"}), PEnters("kyle", "hall"))
        self.assertRaises(KeyError, p.expand_pattern, {"y" : 1})


class TestRuleTable(unittest.TestCase) :
    def test_reverse_order_and_matching(self) :
        """Handlers run in reverse definition order; non-matching
        handlers are skipped."""
        table = RuleTable()
        calls = []

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            calls.append("h1:" + x)

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h2(x) :
            calls.append("h2:" + x)

        @make_rule_decorator(table)(PEnters("bob", X))
        def h3(x) :
            calls.append("h3:" + x)

        table.notify(PEnters("kyle", "hall"), {})
        self.assertEqual(calls, ["h2:hall", "h1:hall"])

    def test_notify_leaves_disabled_stack_balanced(self) :
        """After notify returns (normally or via exceptions), the
        temporary-disable stack must be restored; otherwise disable
        state leaks between notifications and the stack grows without
        bound."""
        table = RuleTable()

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            return None

        self.assertIsNone(table.current_disabled)
        table.notify(PEnters("kyle", "hall"), {})
        table.notify(PEnters("kyle", "hall"), {})
        self.assertIsNone(table.current_disabled)
        self.assertEqual(table.last_current_disabled, [])

    def test_nested_notify_leaves_disabled_stack_balanced(self) :
        """A handler which itself notifies a rule table must not
        corrupt the disable bookkeeping of either table."""
        inner = RuleTable()
        outer = RuleTable()

        @make_rule_decorator(inner)(PEnters("kyle", X))
        def h_inner(x) :
            return None

        @make_rule_decorator(outer)(PEnters("kyle", X))
        def h_outer(x) :
            inner.notify(PEnters("kyle", "inner"), {})

        outer.notify(PEnters("kyle", "outer"), {})
        self.assertIsNone(inner.current_disabled)
        self.assertIsNone(outer.current_disabled)
        self.assertEqual(inner.last_current_disabled, [])
        self.assertEqual(outer.last_current_disabled, [])

    def test_multiple_results(self) :
        """A handler raising MultipleResults contributes several
        values to the accumulator."""
        table = RuleTable(accumulator=list)

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            raise MultipleResults("a", "b")

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h2(x) :
            return "c"

        self.assertEqual(table.notify(PEnters("kyle", "hall"), {}), ["c", "a", "b"])

    def test_finish_with_and_restart_with(self) :
        table = RuleTable(accumulator=list)

        # registered first, so (reverse order) it runs last
        @make_rule_decorator(table)(PEnters("kyle", X))
        def h2(x) :
            raise FinishWith("b")

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            return "a"

        self.assertEqual(table.notify(PEnters("kyle", "hall"), {}), ["a", "b"])

        table2 = RuleTable(accumulator=list)

        @make_rule_decorator(table2)(PEnters("kyle", X))
        def g2(x) :
            raise RestartWith("z")

        @make_rule_decorator(table2)(PEnters("kyle", X))
        def g1(x) :
            return "a"

        self.assertEqual(table2.notify(PEnters("kyle", "hall"), {}), ["z"])

    def test_action_handled_stops(self) :
        table = RuleTable(accumulator=list)
        calls = []

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            calls.append("h1")

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h2(x) :
            calls.append("h2")
            raise ActionHandled("done")

        self.assertEqual(table.notify(PEnters("kyle", "hall"), {}), ["done"])
        self.assertEqual(calls, ["h2"])

    def test_not_handled_skips(self) :
        table = RuleTable(accumulator=list)

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            raise NotHandled()

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h2(x) :
            return "ran"

        self.assertEqual(table.notify(PEnters("kyle", "hall"), {}), ["ran"])

    def test_disable_and_temp_disable(self) :
        """disable/temp_disable rely on being able to find handlers in
        the table (regression: they referenced an undefined
        list_append)."""
        table = RuleTable(accumulator=list)
        calls = []

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            calls.append("h1")

        table.disable(h1)
        table.notify(PEnters("kyle", "hall"), {})
        self.assertEqual(calls, [])

        table2 = RuleTable(accumulator=list)
        calls2 = []

        @make_rule_decorator(table2)(PEnters("kyle", X))
        def g1(x) :
            calls2.append("g1")

        table2.notify(PEnters("kyle", "hall"), {}, disable=[g1])
        self.assertEqual(calls2, [])
        # the disable was temporary:
        table2.notify(PEnters("kyle", "hall"), {})
        self.assertEqual(calls2, ["g1"])

    def test_copy_isolation(self) :
        table = RuleTable(accumulator=list)

        @make_rule_decorator(table)(PEnters("kyle", X))
        def h1(x) :
            return "orig"

        copied = table.copy()

        @make_rule_decorator(copied)(PEnters("kyle", X))
        def h2(x) :
            return "new"

        self.assertEqual(table.notify(PEnters("kyle", "hall"), {}), ["orig"])
        self.assertEqual(copied.notify(PEnters("kyle", "hall"), {}), ["new", "orig"])


class TestActivityTable(unittest.TestCase) :
    def test_runs_all_and_accumulates(self) :
        table = ActivityTable(accumulator=list)
        table.add_handler(lambda : "a")
        table.add_handler(lambda : "b")
        self.assertEqual(table.notify((), {}), ["a", "b"])

    def test_insert_after(self) :
        """insert_after must position relative to the insert_after
        function (regression: it looked up insert_before instead)."""
        table = ActivityTable(accumulator=list)
        table.add_handler(lambda : "a")
        def b() : return "b"
        table.add_handler(b)
        table.add_handler(lambda : "c", insert_after=b)
        self.assertEqual(table.notify((), {}), ["a", "b", "c"])

    def test_insert_before(self) :
        table = ActivityTable(accumulator=list)
        table.add_handler(lambda : "a")
        def b() : return "b"
        table.add_handler(b)
        table.add_handler(lambda : "c", insert_before=b)
        self.assertEqual(table.notify((), {}), ["a", "c", "b"])

    def test_abort_action_stops(self) :
        table = ActivityTable(accumulator=list)
        calls = []
        def a() :
            calls.append("a")
            raise AbortAction()
        table.add_handler(a)
        table.add_handler(lambda : calls.append("b"))
        self.assertRaises(AbortAction, table.notify, (), {})
        self.assertEqual(calls, ["a"])

    def test_disable_stack_balanced(self) :
        table = ActivityTable(accumulator=list)
        table.add_handler(lambda : None)
        table.notify((), {})
        self.assertIsNone(table.current_disabled)
        self.assertEqual(table.last_current_disabled, [])


class TestPropertyTable(unittest.TestCase) :
    def test_set_and_get(self) :
        table = PropertyTable()
        table[PEnters("kyle", "hall")] = 42
        self.assertEqual(table.get_property(PEnters("kyle", "hall"), {}), 42)
        self.assertRaises(KeyError, table.get_property, PEnters("kyle", "elsewhere"), {})

    def test_newest_wins(self) :
        table = PropertyTable()
        table[PEnters("kyle", "hall")] = 1
        table[PEnters("kyle", "hall")] = 2
        self.assertEqual(table.get_property(PEnters("kyle", "hall"), {}), 2)

    def test_pattern_matching_with_vars(self) :
        table = PropertyTable()
        table[PEnters("kyle", X)] = "matched"
        self.assertEqual(table.get_property(PEnters("kyle", "anywhere"), {}), "matched")

    def test_handler_called_with_data(self) :
        table = PropertyTable()

        @table.handler(PEnters("kyle", X))
        def h(x, world) :
            return (x, world)

        self.assertEqual(table.get_property(PEnters("kyle", "hall"), {"world" : "W"}),
                         ("hall", "W"))

    def test_copy_isolation(self) :
        table = PropertyTable()
        table[PEnters("kyle", "hall")] = 1
        copied = table.copy()
        copied[PEnters("kyle", "hall")] = 2
        self.assertEqual(table.get_property(PEnters("kyle", "hall"), {}), 1)
        self.assertEqual(copied.get_property(PEnters("kyle", "hall"), {}), 2)


if __name__ == "__main__" :
    unittest.main()
