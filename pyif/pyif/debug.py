
from . import glk

# Debug output is off in normal play.  Set this to True (or call a story's
# debug entry point) to see parser/action trace output.
enabled = False

def log(string):
    if enabled:
        glk.put_string("[LOG] %s\n" % string)
