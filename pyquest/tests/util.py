"""Shared fixtures: a small ASLX game exercised by the whole suite."""
import contextlib
import io
import os
import tempfile
import unittest

from pyquest.game import QuestGame

GAME_XML = """<asl version="580">
  <game name="TestGame">
    <gameid>testgame</gameid>
    <version>1.0</version>
    <author>tester</author>
    <start type="script">msg ("Welcome!")</start>
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
  <function name="AddGold" parameters="amount"><![CDATA[player.gold = player.gold + amount]]></function>
</asl>
"""


def make_game():
    fd, path = tempfile.mkstemp(suffix=".aslx")
    with os.fdopen(fd, "w") as fh:
        fh.write(GAME_XML)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            game = QuestGame(path, from_qfile=False)
    finally:
        os.unlink(path)
    return game


class GameTestCase(unittest.TestCase):
    def setUp(self):
        self.game = make_game()
        self.player = self.game.objects["player"]

    def run_script(self, code, name="test"):
        """Run an inline script, capturing anything it prints."""
        from pyquest.script_engine import Script
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = Script(name, code)()
        return result, out.getvalue()

    def call_function(self, name, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = self.game.script_engine.functions[name](*args)
        return result, out.getvalue()
