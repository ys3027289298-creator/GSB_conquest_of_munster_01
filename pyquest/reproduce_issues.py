"""Reproduction script for six pyquest engine issues.

Run:  python3 reproduce_issues.py
Exits 0 when all six behaviours are correct, 1 otherwise.
Before the engine fix, every check below fails (the bug is reproduced).
"""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from pyquest.game import QuestGame
from pyquest.script_engine import Script

try:
    from pyquest.errors import UndefinedJumpError, MissingObjectError
except ImportError:  # engine not fixed yet
    UndefinedJumpError = MissingObjectError = None

GAME_XML = """<asl version="580">
  <game name="ReproGame">
    <gameid>repro</gameid>
    <version>1.0</version>
    <author>pyquest</author>
    <start type="script">msg ("Welcome to the repro game.")</start>
  </game>
  <object name="cave">
    <object name="player">
      <attr name="gold" type="int">5</attr>
      <attr name="inventory" type="stringlist">
        <value>rope</value>
        <value>torch</value>
      </attr>
    </object>
    <object name="sword"/>
  </object>
  <object name="hall"/>
  <object name="bell">
    <attr name="ring" type="script"></attr>
  </object>
  <function name="EnterHall"><![CDATA[firsttime {
  msg ("You enter the hall for the first time.")
}
otherwise {
  msg ("You enter the hall again.")
}]]></function>
  <function name="LootCorpse"><![CDATA[foreach (item, player.inventory) {
  player.gold = player.gold + 1
}]]></function>
</asl>
"""


def make_game():
    fd, path = tempfile.mkstemp(suffix=".aslx")
    with os.fdopen(fd, "w") as fh:
        fh.write(GAME_XML)
    with contextlib.redirect_stdout(io.StringIO()):
        game = QuestGame(path, from_qfile=False)
    os.unlink(path)
    return game


def check(label, fn):
    try:
        ok, detail = fn()
    except Exception as err:  # noqa: BLE001 - repro script reports everything
        ok, detail = False, "unexpected %s: %s" % (type(err).__name__, err)
    print("[%s] %s -- %s" % ("OK" if ok else "REPRODUCED", label, detail))
    return ok


def issue_empty_script():
    game = make_game()
    ring = game.objects["bell"].ring
    if not isinstance(ring, Script):
        return False, "bell.ring is %r, expected a Script" % type(ring).__name__
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = ring()
    except Exception as err:
        return False, "empty script crashed with %s: %s" % (type(err).__name__, err)
    return result is None, "empty script ran, returned %r" % (result,)


def issue_undefined_jump():
    game = make_game()
    jumper = Script("repro->jump", "GoToHall ()")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            jumper()
    except Exception as err:
        if UndefinedJumpError is not None and isinstance(err, UndefinedJumpError):
            return True, "raised UndefinedJumpError(%s)" % (err,)
        return False, "raised raw %s: %s" % (type(err).__name__, err)
    return False, "call to undefined function silently succeeded"


def issue_missing_object():
    game = make_game()
    if not hasattr(game, "get_object"):
        return False, "QuestGame has no get_object(); objects['ghost'] raises bare KeyError"
    try:
        game.get_object("ghost")
    except Exception as err:
        if MissingObjectError is not None and isinstance(err, MissingObjectError):
            break_ok = True
        else:
            return False, "raised raw %s: %s" % (type(err).__name__, err)
    else:
        return False, "missing object lookup silently succeeded"
    # a failed move must not corrupt world state
    sword = game.objects["sword"]
    before = sword.parent
    if not hasattr(game.script_engine, "run_safe"):
        return False, "ScriptEngine has no run_safe() failure-recovery API"
    mover = Script("repro->move", "MoveObject (sword, \"nowhere\")")
    err = game.script_engine.run_safe(mover)
    if MissingObjectError is not None and not isinstance(err, MissingObjectError):
        return False, "run_safe captured %r instead of MissingObjectError" % (err,)
    if sword.parent is not before:
        return False, "failed MoveObject still mutated sword.parent"
    return break_ok, "MissingObjectError raised; failed move left world state intact"


def issue_loop_events():
    game = make_game()
    player = game.objects["player"]
    with contextlib.redirect_stdout(io.StringIO()):
        game.script_engine.functions["LootCorpse"]()
    gold = str(player.gold)
    return gold == "7", "after foreach over 2 items, player.gold = %s (expected 7)" % gold


def issue_player_state_not_saved():
    game = make_game()
    if not (hasattr(game, "save_state") and hasattr(game, "load_state")):
        return False, "QuestGame has no save_state()/load_state()"
    player = game.objects["player"]
    player.gold = 99
    state = game.save_state()
    player.gold = 0
    game.load_state(state)
    gold = str(game.objects["player"].gold)
    return gold == "99", "after save/mutate/load, player.gold = %s (expected 99)" % gold


def issue_event_rerun():
    game = make_game()
    enter = game.script_engine.functions["EnterHall"]
    out1, out2 = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out1):
            enter()
        with contextlib.redirect_stdout(out2):
            enter()
    except Exception as err:
        return False, "event script crashed with %s: %s" % (type(err).__name__, err)
    first = "first time" in out1.getvalue()
    second = "again" in out2.getvalue() and "first time" not in out2.getvalue()
    detail = "run1=%r run2=%r" % (out1.getvalue().strip(), out2.getvalue().strip())
    return first and second, detail


def main():
    checks = [
        ("empty script", issue_empty_script),
        ("undefined jump", issue_undefined_jump),
        ("missing object", issue_missing_object),
        ("loop events (foreach)", issue_loop_events),
        ("player state not saved", issue_player_state_not_saved),
        ("same event executed repeatedly", issue_event_rerun),
    ]
    results = [check(label, fn) for label, fn in checks]
    print("\n%d/%d checks pass" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
