"""Test harness for underground/main.py.

Loads the game module without running its interactive entry points
(main_menu / game_loop autorun) and without real sleeps, screen clears
or tkinter dialogs. The game source itself is never modified.
"""

import contextlib
import io
import os
import re
import sys
import types
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "main.py")


class StopGame(Exception):
    """Raised by the mocked input() when scripted replies run out."""


def load_module():
    """Exec main.py in a fresh module namespace and return it."""
    tk = types.ModuleType("tkinter")
    tkm = types.ModuleType("tkinter.messagebox")
    tkm.showerror = lambda *a, **k: None
    tk.messagebox = tkm
    sys.modules["tkinter"] = tk
    sys.modules["tkinter.messagebox"] = tkm

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    with open(MAIN, encoding="utf-8") as f:
        src = f.read()
    # Disable only the interactive autorun entry points.
    src = re.sub(r"(?m)^main_menu\(\)$", "pass  # test harness", src)
    src = re.sub(r"(?m)^game_loop\(\)$", "pass  # test harness", src)

    module = types.ModuleType("underground_main")
    module.__file__ = MAIN
    with mock.patch("time.sleep", lambda *a, **k: None), \
         mock.patch("os.system", lambda *a, **k: 0), \
         contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, MAIN, "exec"), module.__dict__)

    # Deterministic, fast replacements for test runs.
    module.sleep = lambda *a, **k: None
    module.cls = lambda: None
    module.wprint = lambda text="", delay="1": print(text)
    module.dprint = lambda text="", delay="1": print(text)
    return module


def make_input(script):
    """Return an input() replacement feeding scripted replies."""
    replies = iter(script)

    def fake_input(prompt=""):
        print(prompt, end="")
        try:
            reply = next(replies)
        except StopIteration:
            raise StopGame()
        print(reply)
        return reply

    return fake_input
