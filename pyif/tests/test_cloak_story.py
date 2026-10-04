"""End-to-end smoke test for the bundled Cloak of Darkness story.

The story module calls glk.main() on import, so the test installs the
scripted glk backend and replaces glk.main with a direct invocation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_pyif import ScriptedGlk
from pyif import glk, debug, message


def run_cloak(commands):
    debug.set_enabled(False)
    scripted = ScriptedGlk(list(commands) + ["quit"])
    glk.get_string = scripted.get_string
    glk.put_string = scripted.put_string
    glk.put_char = scripted.put_char
    glk.set_style = scripted.set_style

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    story_path = os.path.join(root, "cloak.py")

    saved_main = glk.main
    namespace = {}
    try:
        glk.main = lambda fn: fn()
        with open(story_path) as fh:
            exec(compile(fh.read(), story_path, "exec"), namespace)
    finally:
        glk.main = saved_main
    return scripted.output.getvalue()


class CloakSmokeTest(unittest.TestCase):

    def test_full_session(self):
        out = run_cloak([
            "verbose",          # mode persists
            "w",                # into the cloakroom
            "examine hook",     # callable description must not crash
            "e",                # back to the foyer
            "eat foo",          # HELD_TOKEN verb + implicit take
            "xyzzy",            # unknown verb
            "take t2",          # not a known noun -> parse error
            "drop cloak",       # blocked outside the cloakroom
            "w",
            "take bar",         # known noun but out of scope -> CANT_SEE
            "drop cloak",       # drops on the hook; bar becomes lit
            "tree",             # debug verb must not exist in release
            "quit",
        ])
        self.assertIn("Foyer of the Opera House", out)
        self.assertIn("small brass hook", out)
        self.assertIn(message.FIRST_TAKING % ("a", "foo"), out)
        self.assertIn(message.NOT_A_VERB, out)
        self.assertIn(message.UNDERSTAND_AS_FAR % "take", out)
        self.assertIn(message.CANT_SEE_A % "bar", out)
        self.assertIn(
            "This isn't the best place to leave a smart cloak lying around.", out)
        self.assertIn(message.DROPPED, out)
        self.assertIn(message.NOT_A_VERB, out)
        self.assertNotIn("[LOG]", out)


if __name__ == "__main__":
    unittest.main()
