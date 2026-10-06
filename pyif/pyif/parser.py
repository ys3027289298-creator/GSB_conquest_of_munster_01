#from . import action
from . import action
from . import glk
from . import message
from .debug import log

#from . import *

NOUN_TOKEN        = 1
HELD_TOKEN        = 2
MULTI_TOKEN       = 3
MULTIHELD_TOKEN   = 4
MULTIEXCEPT_TOKEN = 5
MULTIINSIDE_TOKEN = 6
TOPIC_TOKEN       = 7
CREATURE_TOKEN    = 8

# Token types whose noun must be held by the actor
HELD_TOKEN_TYPES = (HELD_TOKEN, MULTIHELD_TOKEN)

def tokenise_string(string):
    "Transform the string into a list of tokens"
    tokens = []
    start = 0
    for i in range(len(string)):
        if string[i] == " ":
            if start < i:
                tokens.append(string[start:i])
            start = i + 1
    if len(string) > 0 and start <= i:
        tokens.append(string[start:i + 1])
    return tokens

class Parser:
    """Inputs commands from the user and executes them.
    
    At the moment this is very simple -- just enough to get us going.
    """
    
    def __init__(self, story, grammar):
        self.story = story
        self.grammar = grammar
        
    def read_input(self):
        """
        Parser strategy:
        * Break input into tokens
        * Match the initial token with a verb definition in the grammar
        """

        glk.put_string("\n>")
        line = glk.get_string()
        tokens = tokenise_string(line.lower())
        
        # Fresh turn: make sure no action/nouns leak in from the previous
        # command
        self.story.actor = self.story.player
        self.story.action = None
        self.story.nouns = []

        if len(tokens) == 0:
            glk.put_string(message.PARDON);
            return True
        
        # Find the Verb that handles this
        verb = self.grammar.find_verb_matching_token(tokens[0])
        if verb:
            log("matched: " + tokens[0])
            
            a, noun_tokens_and_types = verb.find_action_matching_tokens(tokens[1:])
            
            if a:
                log("ACTION: %s, MATCHED NOUNS: %s" % (a[1], noun_tokens_and_types))

                # Set the pending action before noun resolution, so that an
                # implicit take sees the real action in before/after hooks
                self.story.action = a[1]

                matched_nouns = []
                for noun_token, noun_type in noun_tokens_and_types:
                    n = self.ensure_noun_token_in_scope(noun_token, noun_type)
                    if not n:
                        # The scope check already printed the relevant
                        # message ("I can't see...", disambiguation, ...)
                        return True
                    matched_nouns.append(n)

                self.story.nouns = matched_nouns

                # Substitute nouns if we have them (e.g. directions)
                if a[2]:
                    self.story.nouns = a[2]

                # Execute the action
                a[1](self.story)

                return not self.story.has_quit
            else:
                log("NO ACTION MATCH")

            glk.put_string(message.UNDERSTAND_AS_FAR % verb.verb_tokens[0])
            return True

        glk.put_string(message.NOT_A_VERB)
        return True
            
    def ensure_noun_token_in_scope(self, noun_token, noun_type):

        room = self.story.player.room()

        if noun_type in HELD_TOKEN_TYPES:

            # Are we already holding the noun?
            matches = self.story.actor.find_all(noun_token)
            n = self._choose(matches)
            if n:
                log("matched held noun: " + n.name)
                return n

            # Not holding it -- is it visible so we can implicitly take it?
            matches = room.find_all(noun_token)
            if not matches:
                glk.put_string(message.CANT_SEE_A % noun_token)
                return None
            n = self._choose(matches)
            if not n:
                return None

            glk.put_string(message.FIRST_TAKING % (n.article, n.name))

            # Perform the take as a nested action, then restore the outer
            # action/nouns so the result is not visible as a stray 'take'
            saved_nouns = self.story.nouns
            saved_action = self.story.action
            saved_silent = self.story.keep_silent
            self.story.nouns = [n]
            self.story.action = action.take
            self.story.keep_silent = True
            action.take(self.story)
            self.story.nouns = saved_nouns
            self.story.action = saved_action
            self.story.keep_silent = saved_silent

            n = self.story.actor.find(noun_token)
            if not n:
                # The implicit take failed (e.g. scenery); its action
                # already printed the reason
                return None
            log("matched noun after implicit take: " + n.name)
            return n

        else:

            # Room-scope noun
            matches = room.find_all(noun_token)
            if not matches:
                glk.put_string(message.CANT_SEE_A % noun_token)
                return None
            n = self._choose(matches)
            if n:
                log("matched noun: " + n.name)
            return n

    def _choose(self, matches):
        """Return the unique match, or ask the player to disambiguate."""
        if len(matches) == 1:
            return matches[0]
        if len(matches) == 0:
            return None
        names = ["%s %s" % (item.article, item.name) for item in matches]
        glk.put_string(message.WHICH_ONE % message.OR.join(names))
        return None
