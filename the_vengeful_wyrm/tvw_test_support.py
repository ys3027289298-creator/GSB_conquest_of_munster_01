"""
Shared helpers for reproducing and testing the_vengeful_wyrm.

The game modules import third-party packages that are not installed in this
environment (simple_colors, matplotlib, PIL, requests). This module installs
lightweight stubs into sys.modules so the game logic can be imported and
exercised without those dependencies. It also provides:

- FakeInput: deterministic replacement for builtins.input
- NarrativeFixtures: a temp directory with placeholder narrative .txt files
  (the repo ships none); tests chdir into it so open() calls succeed.
"""

import contextlib
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

STUBBED = False


def install_stubs():
    global STUBBED
    if STUBBED:
        return
    sc = types.ModuleType("simple_colors")
    for name in ("red", "green", "blue", "yellow", "magenta", "cyan", "black", "white"):
        setattr(sc, name, (lambda text, *a, **k: str(text)))
    sys.modules["simple_colors"] = sc

    mpl = types.ModuleType("matplotlib")
    mpl.pyplot = types.ModuleType("matplotlib.pyplot")
    sys.modules["matplotlib"] = mpl
    sys.modules["matplotlib.pyplot"] = mpl.pyplot

    pil = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil.Image = pil_image
    sys.modules["PIL"] = pil
    sys.modules["PIL.Image"] = pil_image

    req = types.ModuleType("requests")

    class RequestException(Exception):
        pass

    req.exceptions = types.SimpleNamespace(RequestException=RequestException)

    def _get(*a, **k):
        raise RequestException("offline stub: no network in tests")

    req.get = _get
    sys.modules["requests"] = req
    STUBBED = True


class FakeInput:
    """Deterministic input() replacement feeding a scripted answer queue."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = 0

    def __call__(self, prompt=""):
        self.prompts += 1
        if not self.answers:
            raise AssertionError(
                f"input() called more than {self.prompts - 1} times; "
                "no scripted answers left (unexpected prompt loop?)"
            )
        return self.answers.pop(0)


NARRATIVE_FILES = (
    "intro.txt",
    "dwarf.txt",
    "elf.txt",
    "human.txt",
    "mission.txt",
    "mission_accept.txt",
    "mission_decline.txt",
    "forest.txt",
)


@contextlib.contextmanager
def narrative_cwd():
    """chdir into a temp dir containing placeholder narrative text files."""
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        for name in NARRATIVE_FILES:
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                fh.write(f"TEST FIXTURE narrative ({name})")
        os.chdir(tmp)
        try:
            yield tmp
        finally:
            os.chdir(old)


@contextlib.contextmanager
def patched(**patches):
    """Patch attributes: patched(module_obj, name=value) via keyword 'mod__attr'."""
    originals = []
    try:
        for dotted, value in patches.items():
            module_name, attr = dotted.split("__", 1)
            module = sys.modules[module_name]
            originals.append((module, attr, getattr(module, attr)))
            setattr(module, attr, value)
        yield
    finally:
        for module, attr, old in originals:
            setattr(module, attr, old)
