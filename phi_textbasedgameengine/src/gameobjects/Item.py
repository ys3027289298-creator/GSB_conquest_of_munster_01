from random import randint
from typing import List
import re
from game.GameError import GameError
from game.YamlUtil import YamlUtil
from gameobjects.GameObject import GameObject


def tokenize(effect):
    tokens = []
    token = ''
    capture = False
    effect = re.sub(' +', ' ', effect.lower().strip())
    for ch in effect:
        if ch == ' ' and not capture:
            tokens.append(token)
            token = ''
        elif ch == '(':
            capture = True
        elif ch == ')':
            if not capture:
                raise GameError(f'Invalid formatting: "{effect}"')
            capture = False
        else:
            token += ch
    if capture:
        raise GameError(f'Invalid formatting: "{effect}"')
    tokens.append(token)
    return tokens


def select_all(values):
    return list(range(len(values)))

def select_any(values):
    return [0]

def select_random(values):
    return [randint(0, len(values) - 1)]

def select_min(values):
    return [min(range(len(values)), key=values.__getitem__)]

def select_max(values):
    return [max(range(len(values)), key=values.__getitem__)]


MODIFIERS = {
    'add': lambda ctx, obj, prop, value, name: update_prop(ctx, obj, prop, value, name, +1),
    'sub': lambda ctx, obj, prop, value, name: update_prop(ctx, obj, prop, value, name, -1),
    'use': lambda ctx, obj, prop, value, name: obj.use(ctx),
    'say': lambda ctx, obj, prop, value, name: ctx.send(str(value)),
    'spawn': lambda ctx, obj, prop, value, name: ctx.spawn(name),
    'destroy': lambda ctx, obj, prop, value, name: ctx.destroy(obj)
}

WHICH = {
    'all': select_all,
    'any': select_any,
    'random': select_random,
    'min': select_min,
    'max': select_max
}


def update_prop(ctx, obj, prop, value, name, sign):
    if prop is None:
        raise GameError(f'Cannot modify "{name}" directly, a property is required (e.g. {name}.health)')
    if not hasattr(obj, prop):
        raise GameError(f'Object "{name}" has no property "{prop}"')
    current = getattr(obj, prop)
    setattr(obj, prop, current + sign * value)

class Item(GameObject):
    """
    An item object enables developers to add usable/interactable that the player
    can pickup, drop, and use.

    @author Nausher Rao (SherRao#8509)
    @author Jacob Heard
    """
    
    def __init__(self):
        super().__init__()

    def use(self, game_ctx):
        self.uses -= 1
        if self.uses == 0:
            game_ctx.destroy(self)
        for effect in self.effects:
            effect(game_ctx)

    @staticmethod
    def parse_effects(effects: List[str]):
        return [Item.parse_effect(e) for e in effects]

    @staticmethod
    def parse_effect(effect: str):
        if not isinstance(effect, str) or not effect.strip():
            raise GameError(f'Invalid formatting: "{effect}"')

        # 'say' prints free-form text and is parsed before generic tokenization
        say_match = re.fullmatch(r'say\s*\((.*)\)', effect.strip(), flags=re.DOTALL | re.IGNORECASE)
        if say_match:
            message = say_match.group(1)
            return lambda game_ctx: game_ctx.send(message)

        tokens = tokenize(effect)

        modifier_name = tokens[0]
        if modifier_name not in MODIFIERS:
            raise GameError(f'Invalid modifier "{modifier_name}" in effect: "{effect}"')
        modifier = MODIFIERS[modifier_name]

        rest = tokens[1:]
        index = 0
        if rest and rest[index].lstrip('-+').isdigit():
            value = int(rest[index])
            index += 1
        else:
            value = 0

        if len(rest) > index and rest[index] in WHICH:
            which = WHICH[rest[index]]
            index += 1
        else:
            which = WHICH['any']

        if len(rest) <= index:
            raise GameError(f'Invalid formatting: "{effect}"')
        # Object names may contain spaces, so the target is every remaining token
        target = ' '.join(rest[index:])
        if not target:
            raise GameError(f'Invalid formatting: "{effect}"')
        if '.' in target:
            name, prop = target.rsplit('.', 1)
            if not name or not prop:
                raise GameError(f'Invalid formatting: "{effect}"')
        else:
            name, prop = target, None

        def call(game_ctx):
            # Spawn looks up a template, not an object already in the context
            if modifier_name == 'spawn':
                modifier(game_ctx, None, prop, value, name)
                return

            matches = [obj for obj in game_ctx.objects.values()
                       if YamlUtil.simplify_name(getattr(obj, 'name', '')) == name]
            if not matches:
                raise GameError(f'Unknown object "{name}" in effect: "{effect}"')
            if prop is None:
                values = matches
            else:
                values = []
                for match in matches:
                    if not hasattr(match, prop):
                        raise GameError(f'Object "{name}" has no property "{prop}"')
                    values.append(getattr(match, prop))

            for selected in which(values):
                modifier(game_ctx, matches[selected], prop, value, name)
        return call

    attributes = {
        'name': (True, lambda x: x),
        'description': (False, lambda x: x),
        'uses': (True, int),
        'effects': (True, parse_effects)
    }

