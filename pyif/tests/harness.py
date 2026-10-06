"""Scripted-input harness for driving the pyif parser in tests.

The real glk module talks to curses; here we patch it with a fake that
feeds lines from a script and captures all output, so tests can assert on
both the text the player sees and the resulting world state.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyif import glk
from pyif.story import Story
from pyif import thing
from pyif import action


class ScriptedGlk:
    """Drop-in replacement for the glk module used by the engine."""

    def __init__(self, script):
        self.script = list(script)
        self.output = []

    def install(self):
        glk.put_string = self.put_string
        glk.put_char = self.put_char
        glk.set_style = self.set_style
        glk.get_string = self.get_string

    def put_string(self, string):
        self.output.append(str(string))

    def put_char(self, char):
        self.output.append(str(char))

    def set_style(self, style):
        pass

    def get_string(self):
        if not self.script:
            return "quit"
        return self.script.pop(0)

    def feed(self, line):
        self.script.append(line)

    @property
    def text(self):
        return "".join(self.output)


def make_story(script):
    """Build a small test world and return (story, glk, objects dict)."""

    glk_fake = ScriptedGlk(script)
    glk_fake.install()

    story = Story("Test Story", "A test harness story.", None)

    hall = thing.Room("Hall", story.root)
    hall.nouns = ["hall"]
    hall.description = "A bare hall."
    hall.attributes.add(thing.LIGHT)

    cellar = thing.Room("Cellar", story.root)
    cellar.nouns = ["cellar"]
    cellar.description = "An empty cellar with no exits."
    cellar.attributes.add(thing.LIGHT)

    hall.s_to = cellar

    apple = thing.Thing("red apple", hall)
    apple.nouns = ["red", "apple"]
    apple.description = "A shiny red apple."

    coin = thing.Thing("gold coin", hall)
    coin.nouns = ["gold", "coin"]
    coin.description = "A heavy gold coin."

    # Two objects sharing the noun "key" to exercise ambiguity handling.
    brass_key = thing.Thing("brass key", hall)
    brass_key.nouns = ["brass", "key"]
    brass_key.description = "A brass key."

    iron_key = thing.Thing("iron key", hall)
    iron_key.nouns = ["iron", "key"]
    iron_key.description = "An iron key."

    rock = thing.Thing("large rock", hall)
    rock.nouns = ["large", "rock"]
    rock.description = "It is firmly embedded."
    rock.attributes.add(thing.SCENERY)

    cloak = thing.Thing("black cloak", story.player)
    cloak.nouns = ["black", "cloak"]
    cloak.description = "A black cloak."
    cloak.attributes.add(thing.CLOTHING)
    cloak.attributes.add(thing.WORN)

    thing.move(story.player, hall)

    objects = {
        "hall": hall,
        "cellar": cellar,
        "apple": apple,
        "coin": coin,
        "brass_key": brass_key,
        "iron_key": iron_key,
        "rock": rock,
        "cloak": cloak,
    }
    return story, glk_fake, objects


def run_script(script):
    """Run a story through a scripted list of commands.

    Returns (story, glk, objects). The script is padded with "quit" so the
    story loop always terminates.
    """
    story, glk_fake, objects = make_story(list(script) + ["quit"])
    story.run()
    return story, glk_fake, objects
