"""Reproduction harness (before fixes). Scripted input/output, no curses."""
import sys, io, traceback
sys.path.insert(0, __file__.rsplit("/", 2)[0])

from pyif import glk, thing

# Scripted glk backend
class FakeGlk:
    def __init__(self, commands):
        self.commands = list(commands)
        self.output = io.StringIO()
    def get_string(self):
        return self.commands.pop(0)
    def put_string(self, s):
        self.output.write(s)
    def put_char(self, c):
        self.output.write(c)
    def set_style(self, style):
        pass

def run(commands):
    fake = FakeGlk(commands)
    glk.get_string = fake.get_string
    glk.put_string = fake.put_string
    glk.put_char = fake.put_char
    glk.set_style = fake.set_style
    return fake

def build_world():
    from pyif.story import Story
    story = Story("Test", "test world", None)
    room_a = thing.Room("Room A", story.root); room_a.nouns=["a"]
    room_a.description = "Room A."
    room_a.attributes.add(thing.LIGHT)
    room_b = thing.Room("Room B", story.root); room_b.nouns=["b"]
    room_b.description = "Room B."
    room_b.attributes.add(thing.LIGHT)
    room_a.w_to = room_b
    room_b.e_to = room_a
    thing.move(story.player, room_a)
    foo = thing.Thing("red ball", room_a); foo.nouns=["ball"]
    bar = thing.Thing("red box", room_a); bar.nouns=["box"]
    return story, room_a, room_b, foo, bar

def section(title):
    print("\n===== %s =====" % title)

def show(fake, story, label):
    out = fake.output
    print("--- %s" % label)
    print(out.getvalue().strip() or "(no output)")

# 0. import
section("0 import Story")
try:
    from pyif.story import Story
    print("import ok")
except Exception as e:
    traceback.print_exc()
    sys.exit(0)

story, room_a, room_b, foo, bar = build_world()

# 1. unrecognized verb: 'eat ball' needs HELD_TOKEN matching
section("1 valid verb with held object: eat ball")
out = run(["eat ball", "quit"])
try:
    while story.parser.read_input(): pass
except Exception:
    traceback.print_exc()
show(out, story, "eat ball")

# 2. ambiguous object: both share noun 'red'
foo.nouns.append("red"); bar.nouns.append("red")
section("2 ambiguous: take red")
out = run(["take red", "quit"])
try:
    while story.parser.read_input(): pass
except Exception:
    traceback.print_exc()
show(out, story, "take red")
print("parent of ball:", foo.parent.name, "| parent of box:", bar.parent.name)

# rebuild for remaining tests
story, room_a, room_b, foo, bar = build_world()

# 3. empty room: room with no exit attributes, move into it
room_c = thing.Room("Empty Room", story.root); room_c.nouns=["c"]
room_c.description = "Empty."
room_c.attributes.add(thing.LIGHT)
room_a.s_to = room_c
section("3 empty room with no exits: s then n/e/w")
out = run(["s", "n", "e", "w", "quit"])
try:
    while story.parser.read_input(): pass
except Exception:
    traceback.print_exc()
show(out, story, "movement")

story, room_a, room_b, foo, bar = build_world()

# 4. repeated take
section("4 take ball twice")
out = run(["take ball", "take ball", "quit"])
try:
    while story.parser.read_input(): pass
except Exception:
    traceback.print_exc()
show(out, story, "take take")

story, room_a, room_b, foo, bar = build_world()

# 5. action result persistence: verbose mode then move back/forth
section("5 verbose mode must persist")
out = run(["verbose", "w", "e", "quit"])
try:
    while story.parser.read_input(): pass
except Exception:
    traceback.print_exc()
show(out, story, "verbose walk")
print("mode attr on story:", getattr(story, "mode", "<MISSING>"))

story, room_a, room_b, foo, bar = build_world()

# 6. debug leakage: [LOG] lines in normal output + debug verbs
section("6 debug leakage on a normal command")
out = run(["take ball", "quit"])
try:
    while story.parser.read_input(): pass
except Exception:
    traceback.print_exc()
text = out.output.getvalue()
show(out, story, "normal play")
print("[LOG] lines present:", "[LOG]" in text)
print("'tree' registered as a verb in release:",
      story.grammar.find_verb_matching_token("tree") is not None)
