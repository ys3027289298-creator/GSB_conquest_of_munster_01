import pytest
from game.GameContext import GameContext
from game.GameError import GameError
from gameobjects.Item import Item, tokenize
from tests.test_game_utils import MockGameObject, create_object, set_gameobject_id


def fail():
    raise GameError('invalid tokenization')


# tokenize

def test_tokenize_basic():
    assert tokenize('add 5 sword.health', error=fail) == ['add', '5', 'sword.health']

def test_tokenize_keeps_last_token():
    assert tokenize('add 5 sword', error=fail) == ['add', '5', 'sword']

def test_tokenize_captures_parenthesized_spaces():
    assert tokenize('say (hello world)', error=fail) == ['say', 'hello world']

def test_tokenize_unbalanced_close():
    with pytest.raises(GameError):
        tokenize('add 5 )', error=fail)

def test_tokenize_unclosed_open():
    with pytest.raises(GameError):
        tokenize('say (hello', error=fail)

def test_tokenize_nested_open():
    with pytest.raises(GameError):
        tokenize('say ((hello)', error=fail)


# parse_effect input validation

@pytest.mark.parametrize('effect', [
    '',
    'add',
    'add 5',
    'add 5 sword',
    'frobnicate 1 x.y',
    'say',
    'spawn',
])
def test_parse_effect_invalid_input(effect):
    with pytest.raises(GameError):
        Item.parse_effect(effect)


def setup_ctx():
    ctx = GameContext()
    sword = create_object('sword', 1)
    ctx.add(sword)
    return ctx, sword


# modifiers

def test_add_effect_writes_back_to_context_object():
    ctx, sword = setup_ctx()
    Item.parse_effect('add 5 sword.prop')(ctx)
    assert sword.prop == 6
    assert ctx.get_by_id(sword.id).prop == 6

def test_sub_effect_writes_back():
    ctx, sword = setup_ctx()
    sword.prop = 10
    Item.parse_effect('sub 3 sword.prop')(ctx)
    assert ctx.get_by_id(sword.id).prop == 7

def test_effect_unknown_object_raises():
    ctx, _ = setup_ctx()
    effect = Item.parse_effect('add 5 goblin.prop')
    with pytest.raises(GameError):
        effect(ctx)

def test_effect_on_incompatible_property_raises():
    ctx, sword = setup_ctx()
    sword.prop = 'not a number'
    with pytest.raises(GameError):
        Item.parse_effect('add 5 sword.prop')(ctx)


# WHICH selectors

def create_three(ctx):
    set_gameobject_id(10)
    ctx.add(create_object('a', 3))
    ctx.add(create_object('a', 7))
    ctx.add(create_object('a', 5))

def test_selector_all():
    ctx = GameContext()
    create_three(ctx)
    Item.parse_effect('add 2 all a.prop')(ctx)
    assert sorted(o.prop for o in ctx.get_by_name('a')) == [5, 7, 9]

def test_selector_any():
    ctx = GameContext()
    create_three(ctx)
    Item.parse_effect('add 2 any a.prop')(ctx)
    assert [o.prop for o in ctx.get_by_name('a')] == [5, 7, 5]

def test_selector_min():
    ctx = GameContext()
    create_three(ctx)
    Item.parse_effect('add 2 min a.prop')(ctx)
    assert [o.prop for o in ctx.get_by_name('a')] == [5, 7, 5]

def test_selector_max():
    ctx = GameContext()
    create_three(ctx)
    Item.parse_effect('add 2 max a.prop')(ctx)
    assert [o.prop for o in ctx.get_by_name('a')] == [3, 9, 5]

def test_selector_random_single_match():
    ctx, sword = setup_ctx()
    sword.prop = 4
    Item.parse_effect('add 1 random sword.prop')(ctx)
    assert sword.prop == 5


# special modifiers

def test_destroy_effect():
    ctx, sword = setup_ctx()
    Item.parse_effect('destroy sword')(ctx)
    assert ctx.get_by_name('sword') == []

def test_say_effect_sends_message():
    ctx, _ = setup_ctx()
    Item.parse_effect('say (hello world)')(ctx)
    assert ctx.messages == ['hello world']

def test_spawn_effect_unknown_template_raises():
    ctx, _ = setup_ctx()
    with pytest.raises(GameError):
        Item.parse_effect('spawn bat')(ctx)

def test_spawn_effect_adds_new_instance():
    ctx, _ = setup_ctx()
    template = Item.load_from_template(
        {'name': 'bat', 'uses': 1, 'effects': []}, Item)
    ctx.add_template(template)
    spawned = Item.parse_effect('spawn bat')(ctx)
    assert spawned.id != template.id
    assert len(ctx.get_by_name('bat')) == 1
    assert ctx.get_by_id(template.id) is None


# Item lifecycle

def test_item_load_from_template_parses_effects():
    item = Item.load_from_template(
        {'name': 'potion', 'uses': 2, 'effects': ['add 5 sword.prop']}, Item)
    assert item.uses == 2
    assert len(item.effects) == 1
    assert callable(item.effects[0])

def test_item_use_applies_effect_and_stays():
    ctx, sword = setup_ctx()
    item = Item.load_from_template(
        {'name': 'potion', 'uses': 2, 'effects': ['add 5 sword.prop']}, Item)
    ctx.add(item)
    item.use(ctx)
    assert item.uses == 1
    assert ctx.get_by_id(item.id) is item
    assert sword.prop == 6

def test_item_use_destroyed_when_uses_exhausted():
    ctx, sword = setup_ctx()
    item = Item.load_from_template(
        {'name': 'potion', 'uses': 1, 'effects': ['add 5 sword.prop']}, Item)
    ctx.add(item)
    item.use(ctx)
    assert ctx.get_by_id(item.id) is None
    assert sword.prop == 6

def test_item_use_effects_every_use_until_destroyed():
    ctx, sword = setup_ctx()
    item = Item.load_from_template(
        {'name': 'potion', 'uses': 3, 'effects': ['add 5 sword.prop']}, Item)
    ctx.add(item)
    item.use(ctx)
    item.use(ctx)
    item.use(ctx)
    assert ctx.get_by_id(item.id) is None
    assert sword.prop == 16

def test_item_use_effect_uses_another_item():
    ctx, _ = setup_ctx()
    target = Item.load_from_template(
        {'name': 'potion', 'uses': 1, 'effects': []}, Item)
    ctx.add(target)
    user = Item.load_from_template(
        {'name': 'wand', 'uses': 1, 'effects': ['use potion']}, Item)
    ctx.add(user)
    user.use(ctx)
    assert ctx.get_by_id(target.id) is None

def test_item_load_bad_uses_raises():
    with pytest.raises(GameError):
        Item.load_from_template(
            {'name': 'potion', 'uses': 'not_a_number', 'effects': []}, Item)

def test_item_load_invalid_effect_raises():
    with pytest.raises(GameError):
        Item.load_from_template(
            {'name': 'potion', 'uses': 1, 'effects': ['nonsense input']}, Item)
