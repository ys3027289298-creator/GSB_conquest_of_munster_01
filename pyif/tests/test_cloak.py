"""End-to-end scripted playthroughs of cloak.py (the story grammar is
untouched; these tests prove the engine fixes work with a real story)."""

import os
import sys
import unittest

TESTS_DIR = os.path.dirname(__file__)
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, os.path.join(TESTS_DIR, ".."))

from pyif import glk
from harness import ScriptedGlk


def play_cloak(script):
    """Run cloak.py with a scripted input, returning the full output text."""
    fake = ScriptedGlk(list(script) + ["quit"])
    fake.install()
    # Bypass curses: run the story directly
    glk.main = lambda glk_main: glk_main()
    path = os.path.join(TESTS_DIR, "..", "cloak.py")
    with open(path) as f:
        code = f.read()
    exec(compile(code, path, "exec"), {"__name__": "__main__"})
    return fake.text


class TestCloakOfDarkness(unittest.TestCase):
    def test_winning_playthrough(self):
        text = play_cloak([
            "w",                  # to the cloakroom
            "hang cloak on hook", # implicit disrobe, light reaches the bar
            "e",
            "s",                  # bar, now lit
            "x message",          # read the message -> win
        ])
        self.assertIn("You have won", text)
        self.assertNotIn("[LOG]", text)

    def test_blundering_in_the_dark_loses(self):
        text = play_cloak([
            "s",          # bar is dark while wearing the cloak
            "s",          # blundering around...
            "x message",  # message trampled -> lose
        ])
        self.assertIn("Blundering around in the dark", text)
        self.assertIn("In the dark? You could easily disturb something!", text)
        self.assertNotIn("You have won", text)

    def test_uppercase_commands_work_in_story(self):
        text = play_cloak([
            "W",
            "HANG CLOAK ON HOOK",
            "E",
            "S",
            "X MESSAGE",
        ])
        self.assertIn("You have won", text)


if __name__ == "__main__":
    unittest.main()
