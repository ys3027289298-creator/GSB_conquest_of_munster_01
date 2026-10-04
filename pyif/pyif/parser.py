
#from . import action
from . import glk
from . import message
from . import action
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

# Token types that must resolve to an object held by the actor
HELD_LIKE_TOKENS = (HELD_TOKEN, MULTIHELD_TOKEN, MULTIEXCEPT_TOKEN,
                    MULTIINSIDE_TOKEN)

# Returned by ensure_noun_token_in_scope when a noun matches more than
# one object in scope
AMBIGUOUS = object()

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
        tokens = tokenise_string(line)
        
        if len(tokens) == 0:
            glk.put_string(message.PARDON);
            return True

        # Make the actor always the player for the moment
        self.story.actor = self.story.player
        
        # Find the Verb that handles this
        verb = self.grammar.find_verb_matching_token(tokens[0])
        if verb:
            log("matched: " + tokens[0])
            
            a, noun_tokens_and_types = verb.find_action_matching_tokens(tokens[1:])
            
            if a:
                log("ACTION: %s, MATCHED NOUNS: %s" % (a[1], noun_tokens_and_types))
                
                matched_nouns = []
                for noun_token, noun_type in noun_tokens_and_types:
                    if noun_type == TOPIC_TOKEN:
                        # Topics are free text and do not resolve to objects
                        continue
                    n = self.ensure_noun_token_in_scope(noun_token, noun_type)
                    if n is AMBIGUOUS:
                        return True
                    if not n:
                        glk.put_string(message.CANT_SEE_A % noun_token)
                        return True
                    matched_nouns.append(n)

                self.story.action = a[1]
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
        n = None

        # If the noun type is held-like, are we holding the noun?
        if noun_type in HELD_LIKE_TOKENS:
            matches = self.find_all_in_scope(noun_token, self.story.actor)
            if len(matches) > 1:
                return self.report_ambiguous(matches)
            n = matches[0] if matches else None

            # If we're not holding it, so can we see it to do an implicit take?
            if not n and room is not None:
                matches = self.find_all_in_scope(noun_token, room)
                if len(matches) > 1:
                    return self.report_ambiguous(matches)
                if matches:
                    n = matches[0]
                    self.story.nouns = [n]
                    glk.put_string(message.FIRST_TAKING % (n.article, n.name))
                    ks = self.story.keep_silent
                    self.story.keep_silent = True
                    action.take(self.story)
                    self.story.keep_silent = ks
                    n = self.story.actor.find(noun_token)

        elif room is not None:
            matches = self.find_all_in_scope(noun_token, room)
            if len(matches) > 1:
                return self.report_ambiguous(matches)
            n = matches[0] if matches else None

        if n:
            log("matched noun: " + n.name)
            return n

        return None

    def find_all_in_scope(self, noun_token, container):
        "All distinct objects matching the noun token within the container."
        matches = []
        for m in container.find_all(noun_token):
            if m not in matches:
                matches.append(m)
        return matches

    def report_ambiguous(self, matches):
        "Report an ambiguous noun without changing any world state."
        names = ["%s %s" % (m.article, m.name) for m in matches]
        listing = ", ".join(names[:-1])
        if listing:
            listing += " or " + names[-1]
        else:
            listing = names[0]
        glk.put_string(message.WHICH_ONE % listing)
        return AMBIGUOUS
