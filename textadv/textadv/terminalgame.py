# terminalgame.py

# Contains an object which can be used for io in the terminal.

import re
import textwrap

class TerminalGameIO(object) :
    """This class may be replaced in the GameContext by anything which
    implements the following two methods."""
    def __init__(self) :
        self.data = []
    def get_input(self, prompt=">") :
        self.flush()
        try :
            line = input("\n"+prompt + " ")
        except EOFError :
            # The input stream was closed (e.g. Ctrl-D): exit cleanly
            # instead of raising EOFError on every subsequent turn.
            raise SystemExit(0)
        # Strip illegal (control) characters so they cannot confuse
        # the parser or corrupt the terminal output.
        return "".join(c for c in line if c.isprintable() or c == "\t")
    def write(self, *data) :
        self.data.extend(data)
    def set_status_var(self, *args, **kwargs) :
        pass
    def flush(self) :
        d = " ".join(self.data)
        self.data = []
        d = " ".join(re.split("\\s+", d))
        d = re.sub('<[^<]+?>', '', d) # strip out html
        pars = d.replace("[newline]", "\n\n").replace("[break]", "\n").replace("[indent]","  ").split("\n")
        wrapped = ["\n".join(textwrap.wrap(p)) for p in pars]
        print("\n".join(wrapped), end="")
