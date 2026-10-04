import pytest
from game.GameContext import GameContext
from game.GameError import GameError
from gameobjects.Item import Item
from tests.test_game_utils import create_object, set_gameobject_id


def test_add_duplicate_same_object_raises():
    ctx = GameContext()
    obj = create_object('a')
    ctx.add(obj)
    with pytest.raises(GameError):
        ctx.add(obj)

def test_add_duplicate_id_raises():
    ctx = GameContext()
    set_gameobject_id(20)
    first = create_object('a')
    ctx.add(first)
    set_gameobject_id(20)
    second = create_object('b')
    with pytest.raises(GameError):
        ctx.add(second)

def test_add_non_gameobject_raises():
    ctx = GameContext()
    with pytest.raises(AssertionError):
        ctx.add('not a game object')

def test_switch_area_old_objects_inaccessible():
    ctx = GameContext()
    old = create_object('old_item')
    ctx.add(old)
    new = create_object('new_item')

    ctx.switch_area([new])

    assert ctx.get_by_id(old.id) is None
    assert ctx.get_by_name('old_item') == []
    assert ctx.get_by_id(new.id) is new

def test_switch_area_to_empty():
    ctx = GameContext()
    ctx.add(create_object('a'))
    ctx.switch_area([])
    assert ctx.objects == {}

def test_switch_area_rejects_duplicate_objects():
    ctx = GameContext()
    obj = create_object('a')
    with pytest.raises(GameError):
        ctx.switch_area([obj, obj])

def test_send_appends_messages():
    ctx = GameContext()
    ctx.send('hello')
    ctx.send('world')
    assert ctx.messages == ['hello', 'world']

def test_spawn_unknown_raises():
    ctx = GameContext()
    with pytest.raises(GameError):
        ctx.spawn('ghost')

def test_spawn_from_template_new_id_and_added():
    ctx = GameContext()
    template = Item.load_from_template(
        {'name': 'bat', 'uses': 1, 'effects': []}, Item)
    ctx.add_template(template)

    spawned = ctx.spawn('bat')

    assert spawned.id != template.id
    assert spawned.name == 'bat'
    assert ctx.get_by_id(spawned.id) is spawned
    assert ctx.get_by_id(template.id) is None

def test_add_template_non_gameobject_raises():
    ctx = GameContext()
    with pytest.raises(AssertionError):
        ctx.add_template(5)
