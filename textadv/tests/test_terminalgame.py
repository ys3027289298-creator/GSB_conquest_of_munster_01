"""Tests for textadv.terminalgame.TerminalGameIO: input sanitization
and output flushing."""

import io
import unittest
from unittest import mock

from tests import *  # noqa: F401,F403  (sets up sys.path)

from textadv.terminalgame import TerminalGameIO


class TestGetInput(unittest.TestCase) :
    def test_strips_control_characters(self) :
        """Illegal/control characters in terminal input are stripped
        so they cannot confuse the parser or corrupt the display."""
        io_obj = TerminalGameIO()
        with mock.patch("builtins.input", return_value="take \x07the\x0b ball\x7f"):
            self.assertEqual(io_obj.get_input(), "take the ball")

    def test_keeps_normal_input(self) :
        io_obj = TerminalGameIO()
        with mock.patch("builtins.input", return_value="examine the red ball"):
            self.assertEqual(io_obj.get_input(), "examine the red ball")

    def test_eof_exits_cleanly(self) :
        """EOF (Ctrl-D) must not cause an infinite traceback loop; the
        game exits cleanly via SystemExit."""
        io_obj = TerminalGameIO()
        with mock.patch("builtins.input", side_effect=EOFError):
            self.assertRaises(SystemExit, io_obj.get_input)


class TestFlush(unittest.TestCase) :
    def test_flush_strips_html_and_formats(self) :
        io_obj = TerminalGameIO()
        io_obj.write("<b>Hello</b> there[newline]Second paragraph")
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf) :
            io_obj.flush()
        out = buf.getvalue()
        self.assertIn("Hello there", out)
        self.assertNotIn("<b>", out)
        self.assertIn("Second paragraph", out)

    def test_flush_empties_buffer(self) :
        io_obj = TerminalGameIO()
        io_obj.write("something")
        with mock.patch("sys.stdout", io.StringIO()) :
            io_obj.flush()
        self.assertEqual(io_obj.data, [])


if __name__ == "__main__" :
    unittest.main()
