def flatten(list):
    return [item for sublist in list for item in sublist]

def find(item, list):
    return next(x for x in list if item in x.names)

class ScriptError(Exception):
    """Raised when a script cannot be parsed or built into game state.

    Messages are written to be shown directly to game authors: they say
    what is wrong and, when possible, where (line/column).
    """
    pass
