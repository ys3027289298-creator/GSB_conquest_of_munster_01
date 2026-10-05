"""Shared helpers for the pyQuest test suite."""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pyquest.game  # noqa: E402

ASL_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<asl version="550">
  <game name="{name}">
    <gameid>test</gameid>
    <version>1.0</version>
    <author>tester</author>
{start}
  </game>
{extra}
</asl>
"""


def make_game(start=None, extra="", name="testgame"):
    """Build a QuestGame from an in-memory ASLX document."""
    start_tag = ""
    if start is not None:
        start_tag = '    <start type="script">{}</start>'.format(start)
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "game.aslx")
    with open(path, "w") as handle:
        handle.write(ASL_TEMPLATE.format(name=name, start=start_tag, extra=extra))
    return pyquest.game.QuestGame(path, from_qfile=False)


def run_game(game):
    """Run a game, capturing stdout and stderr. Returns (stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        game.run()
    return out.getvalue(), err.getvalue()


def make_and_run(start=None, extra=""):
    game = make_game(start, extra)
    out, err = run_game(game)
    return game, out, err
