
# Debug tracing is disabled by default so it never leaks into the
# release (normal play) flow.  Enable it explicitly with set_enabled().

_enabled = False

def set_enabled(flag):
    global _enabled
    _enabled = bool(flag)

def is_enabled():
    return _enabled

def log(string):
    if _enabled:
        from . import glk
        glk.put_string("[LOG] %s\n" % string)
