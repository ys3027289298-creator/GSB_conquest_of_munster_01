import pytest
from game.GameContext import GameContext
from game.GameError import GameError
from tests.test_game_utils import MockGameObject, create_object, set_gameobject_id


def test_add_returns_true_for_new_object():
	ctx = GameContext()
	obj = create_object('thing')

	result = ctx.add(obj)

	assert result is True

def test_add_same_object_twice_is_idempotent():
	ctx = GameContext()
	obj = create_object('thing')

	assert ctx.add(obj) is True
	assert ctx.add(obj) is False
	assert len(ctx.objects) == 1

def test_destroy_is_idempotent():
	ctx = GameContext()
	obj = create_object('thing')
	ctx.add(obj)

	assert ctx.destroy(obj) is True
	assert ctx.destroy(obj) is False

def test_clear_removes_everything():
	ctx = GameContext()
	obj_a = create_object('a')
	obj_b = create_object('b')
	ctx.add(obj_a)
	ctx.add(obj_b)

	removed = ctx.clear()

	assert sorted(obj.name for obj in removed) == ['a', 'b']
	assert ctx.objects == {}

def test_enter_removes_old_area_objects():
	ctx = GameContext()
	old_npc = create_object('old npc')
	ctx.add(old_npc)

	new_npc = create_object('new npc')
	ctx.enter([new_npc])

	assert ctx.get_by_id(old_npc.id) is None
	assert ctx.get_by_id(new_npc.id) is new_npc
	assert [obj.name for obj in ctx.get_by_name('old npc')] == []

def test_enter_without_objects_empties_context():
	ctx = GameContext()
	ctx.add(create_object('leftover'))

	ctx.enter()

	assert ctx.objects == {}

def test_enter_duplicate_object_within_area_only_added_once():
	ctx = GameContext()
	obj = create_object('thing')

	ctx.enter([obj, obj])

	assert len(ctx.objects) == 1

def test_old_objects_cannot_be_destroyed_after_entering_new_area():
	ctx = GameContext()
	old_obj = create_object('old')
	ctx.add(old_obj)
	ctx.enter([create_object('new')])

	assert ctx.destroy(old_obj) is False

def test_spawn_uses_registered_template():
	ctx = GameContext({'goblin': (MockGameObject, {'name': 'Goblin', 'prop': 3})})

	spawned = ctx.spawn('goblin')

	assert spawned.name == 'Goblin'
	assert spawned.prop == 3
	assert ctx.get_by_id(spawned.id) is spawned

def test_spawn_unknown_name_raises():
	ctx = GameContext()

	with pytest.raises(GameError) as errinfo:
		ctx.spawn('dragon')

	assert 'Cannot spawn unknown object "dragon"' in str(errinfo.value)

def test_spawn_creates_distinct_instances():
	ctx = GameContext({'goblin': (MockGameObject, {'name': 'Goblin'})})

	first = ctx.spawn('goblin')
	second = ctx.spawn('goblin')

	assert first.id != second.id
	assert len(ctx.get_by_name('Goblin')) == 2

def test_send_records_messages():
	ctx = GameContext()

	ctx.send('hello')
	ctx.send('world')

	assert ctx.messages == ['hello', 'world']

def test_add_rejects_non_gameobjects():
	ctx = GameContext()

	with pytest.raises(AssertionError):
		ctx.add('not a game object')
