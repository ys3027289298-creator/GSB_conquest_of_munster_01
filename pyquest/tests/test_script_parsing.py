"""Script parsing: empty scripts, multi-line state, blocks, functions."""
import unittest

from helpers import make_and_run


class ScriptParsingTests(unittest.TestCase):
    def test_empty_script_element_does_not_crash(self):
        # An empty <start type="script"></start> parses with text == None.
        game, out, err = make_and_run(start="")
        self.assertIn("Welcome to", out)
        self.assertEqual(err, "")

    def test_missing_start_element_runs_fine(self):
        game, out, err = make_and_run(start=None)
        self.assertIn("Welcome to", out)
        self.assertEqual(err, "")

    def test_state_persists_across_lines(self):
        code = 'score = 41\nscore = score + 1\nmsg(score)'
        game, out, err = make_and_run(start=code)
        self.assertIn("42", out)
        self.assertEqual(err, "")

    def test_if_else_if_else_blocks(self):
        code = ('if (score = 1) {\n'
                'msg("one")\n'
                '}\n'
                'else if (score = 2) {\n'
                'msg("two")\n'
                '}\n'
                'else {\n'
                'msg("other")\n'
                '}')
        for score, expected in (("1", "one"), ("2", "two"), ("9", "other")):
            game, out, err = make_and_run(start="score = " + score + "\n" + code)
            self.assertIn(expected, out, "score=" + score)
            self.assertEqual(err, "")

    def test_foreach_iterates_string_list(self):
        code = ('items = NewStringList()\n'
                'list add (items, "a")\n'
                'list add (items, "b")\n'
                'foreach (item, items) {\n'
                'msg(item)\n'
                '}')
        game, out, err = make_and_run(start=code)
        self.assertIn("a", out)
        self.assertIn("b", out)
        self.assertEqual(err, "")

    def test_firsttime_then_otherwise(self):
        function = ('<function name="Look">firsttime {\n'
                    'msg("first look")\n'
                    '}\n'
                    'otherwise {\n'
                    'msg("later look")\n'
                    '}</function>')
        game, out, err = make_and_run(start="Look()\nLook()", extra=function)
        self.assertEqual(out.count("first look"), 1)
        self.assertEqual(out.count("later look"), 1)
        self.assertEqual(err, "")

    def test_function_with_parameters_and_return(self):
        function = ('<function name="Double" parameters="x">'
                    'return (x * 2)</function>')
        game, out, err = make_and_run(start="msg(Double(21))", extra=function)
        self.assertIn("42", out)
        self.assertEqual(err, "")

    def test_string_messages_and_markup(self):
        game, out, err = make_and_run(start='msg("Hello&lt;br/&gt;World")')
        self.assertIn("Hello", out)
        self.assertIn("World", out)
        self.assertNotIn("<br/>", out)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
