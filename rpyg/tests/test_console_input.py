"""Saisie console : les choix hors bornes doivent être ré-questionnés, jamais planter."""
import builtins

import pytest

from core.game.actions import NewGame, Quit
from core.ui.console.screens.base_screen import BaseConsoleScreen


class FakeApp:
    def t(self, key, **params):
        return key


class ProbeScreen(BaseConsoleScreen):
    def draw(self):
        pass

    def ask(self):
        return self.choose([("first", NewGame()), ("second", "quit-action")])


def feed(inputs):
    sequence = iter(inputs)

    def fake_input(prompt=""):
        return next(sequence)

    return fake_input


@pytest.mark.parametrize("bad", ["0", "-1", "3", "99", "abc", "", "1.5", "  x "])
def test_out_of_range_choice_is_reasked(monkeypatch, bad):
    screen = ProbeScreen(app=FakeApp())
    monkeypatch.setattr(builtins, "input", feed([bad, "1"]))
    assert isinstance(screen.ask(), NewGame)


def test_valid_choice_after_several_bad_inputs(monkeypatch):
    screen = ProbeScreen(app=FakeApp())
    monkeypatch.setattr(builtins, "input", feed(["99", "0", "abc", "2"]))
    assert screen.ask() == "quit-action"


def test_eof_quits(monkeypatch):
    screen = ProbeScreen(app=FakeApp())

    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    assert isinstance(screen.ask(), Quit)


def test_ctrl_c_quits(monkeypatch):
    screen = ProbeScreen(app=FakeApp())

    def raise_keyboard_interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", raise_keyboard_interrupt)
    assert isinstance(screen.ask(), Quit)
