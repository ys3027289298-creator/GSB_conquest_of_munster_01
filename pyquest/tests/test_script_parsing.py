"""脚本解析: empty scripts, control flow, loops, functions and built-ins."""
from tests.util import GameTestCase

import contextlib
import io



class EmptyScriptTests(GameTestCase):
    def test_empty_string_script_runs(self):
        from pyquest.script_engine import Script
        result = Script("x", "")()
        self.assertIsNone(result)

    def test_none_code_script_runs(self):
        # <attr ... type="script"></attr> parses to Script(name, None).
        ring = self.game.objects["bell"].ring
        result = ring()
        self.assertIsNone(result)


class ControlFlowTests(GameTestCase):
    def test_if_true_branch(self):
        _, out = self.run_script("if (player.gold = 5) {\n  msg (\"rich\")\n}")
        self.assertIn("rich", out)

    def test_if_false_branch(self):
        _, out = self.run_script("if (player.gold = 99) {\n  msg (\"yes\")\n}\n"
                                 "else {\n  msg (\"no\")\n}")
        self.assertIn("no", out)
        self.assertNotIn("yes", out)

    def test_comparison_operators_on_quest_values(self):
        _, out = self.run_script("if (player.gold > 3 and player.gold < 6) {\n"
                                 "  msg (\"between\")\n}")
        self.assertIn("between", out)

    def test_while_loop(self):
        self.run_script("while (player.gold < 8) {\n  player.gold = player.gold + 1\n}")
        self.assertEqual(str(self.player.gold), "8")

    def test_foreach_iterates_every_element(self):
        self.run_script("foreach (item, player.inventory) {\n"
                        "  player.gold = player.gold + 1\n}")
        self.assertEqual(str(self.player.gold), "7")

    def test_foreach_binds_variable(self):
        _, out = self.run_script(
            "foreach (item, player.inventory) {\n  msg (item)\n}")
        self.assertIn("rope", out)
        self.assertIn("torch", out)

    def test_comments_and_blank_lines_ignored(self):
        _, out = self.run_script("// a comment\n\nmsg (\"seen\")\n")
        self.assertIn("seen", out)

    def test_return_value(self):
        from pyquest.script_engine import Script
        result, _ = self.run_script("return player.gold * 2")
        self.assertEqual(result, 10)

    def test_bare_return(self):
        result, _ = self.run_script("return\nmsg (\"unreached\")")
        self.assertIsNone(result)

    def test_function_with_parameters(self):
        result, out = self.call_function("AddGold", 10)
        self.assertEqual(str(self.player.gold), "15")
        self.assertIsNone(result)

    def test_list_add_builtin(self):
        self.run_script("list add (player.inventory, \"gem\")")
        self.assertIn("gem", [str(v) for v in self.player.inventory])

    def test_stringlist_attr_parsed(self):
        self.assertEqual([str(v) for v in self.player.inventory], ["rope", "torch"])

    def test_int_attr_parsed(self):
        self.assertEqual(str(self.player.gold), "5")

    def test_function_registration(self):
        engine = self.game.script_engine
        self.assertTrue(engine.is_function("AddGold"))
        self.assertEqual(engine.functions["AddGold"].parameters, ("amount",))

    def test_firsttime_then_otherwise(self):
        _, first = self.call_function("EnterHall")
        _, second = self.call_function("EnterHall")
        self.assertIn("first time", first)
        self.assertIn("again", second)
        self.assertNotIn("first time", second)

    def test_unterminated_block(self):
        from pyquest.errors import ScriptError
        with self.assertRaises(ScriptError):
            self.run_script("if (true) {\nmsg (\"x\")")

    def test_else_without_if(self):
        from pyquest.errors import ScriptError
        with self.assertRaises(ScriptError):
            self.run_script("else {\nmsg (\"x\")\n}")

    def test_startup_script_runs(self):
        from tests.util import make_game
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            make_game().run()
        self.assertIn("Welcome to TestGame", out.getvalue())
