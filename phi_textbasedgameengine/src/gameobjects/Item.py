from random import randint
from operator import itemgetter
from typing import List
import re
from game.GameError import GameError
from gameobjects.GameObject import GameObject


def tokenize(effect, error):
    tok, toks = '', []
    capture = False
    effect = re.sub(' +', ' ', effect.lower().strip())
    for ch in effect:
        if ch == ' ' and not capture:
            if tok:
                toks.append(tok)
                tok = ''
        elif ch == '(':
            if capture:
                error()
                return
            capture = True
        elif ch == ')':
            if capture:
                capture = False
            else:
                error()
                return
        else:
            tok += ch
    if capture:
        error()
        return
    if tok:
        toks.append(tok)
    return toks

class Item(GameObject):
    """
    An item object enables developers to add usable/interactable that the player
    can pickup, drop, and use.

    @author Nausher Rao (SherRao#8509)
    @author Jacob Heard
    """
    
    attributes = {
        'name': (True, lambda x: x),
        'description': (False, lambda x: x),
        'uses': (True, int),
        'effects': (True, lambda x: Item.parse_effects(x))
    }

    def __init__(self):
        super().__init__()

    def use(self, game_ctx):
        self.uses -= 1
        if self.uses <= 0:
            game_ctx.destroy(self)
        for effect in self.effects:
            effect(game_ctx)

    @staticmethod
    def parse_effects(effects: List[str]):
        return [Item.parse_effect(e) for e in effects]

    @staticmethod
    def parse_effect(effect: str):
        def add(ctx, obj, prop, value):
            setattr(obj, prop, getattr(obj, prop) + value)
        def sub(ctx, obj, prop, value):
            setattr(obj, prop, getattr(obj, prop) - value)
        
        MODIFIERS = {
            'add': add,
            'sub': sub,
            'use': lambda ctx, obj, prop, value: obj.use(ctx),
            'destroy': lambda ctx, obj, prop, value: ctx.destroy(obj)
        }
        WHICH = {
                # f for function, e for entities
                'all': lambda e: list(range(len(e))),
                'any': lambda e: [0],
                'random': lambda e: [randint(0, len(e)-1)],
                'min': lambda e: [min(enumerate(e), key=itemgetter(1))[0]],
                'max': lambda e: [max(enumerate(e), key=itemgetter(1))[0]]
        }

        def raise_err():
            raise GameError(f'Invalid formatting: "{effect}"')
        toks = tokenize(effect, error=raise_err)
        if not toks:
            raise_err()

        # 'say' and 'spawn' do not operate on existing context objects
        if toks[0] == 'say':
            if len(toks) < 2:
                raise_err()
            message = ' '.join(toks[1:])
            return lambda game_ctx: game_ctx.send(message)
        if toks[0] == 'spawn':
            if len(toks) != 2:
                raise_err()
            template_name = toks[1]
            return lambda game_ctx: game_ctx.spawn(template_name)

        # First arg must always be a modifier
        if toks[0] not in MODIFIERS:
            raise GameError(f'Invalid modifier {toks[0]}')
        modifier = MODIFIERS[toks[0]]
        i = 1
        if i < len(toks) and toks[i].lstrip("-+").isdigit():
            value = int(toks[i])
            i += 1
        else:
            value = 0
        if i < len(toks) and toks[i] in WHICH:
            which = WHICH[toks[i]]
            i += 1
        else:
            which = WHICH['any']
        if i >= len(toks):
            raise_err()
        if '.' in toks[i]:
            name, prop = toks[i].split('.', 1)
        else:
            name, prop = toks[i], None
        if modifier in (add, sub) and prop is None:
            raise GameError(f'Modifier "{toks[0]}" requires a property: "{effect}"')

        def call(game_ctx):
            matches = game_ctx.get_by_name(name)
            if not matches:
                raise GameError(f'Unknown object "{name}" in effect "{effect}"')
            values = matches if prop is None else [getattr(obj, prop) for obj in matches]
            indices = which(values)
            for i in indices:
                try:
                    modifier(game_ctx, matches[i], prop, value)
                except GameError:
                    raise
                except (AttributeError, TypeError) as ex:
                    raise GameError(f'Error applying effect "{effect}": {ex}')
        return call

