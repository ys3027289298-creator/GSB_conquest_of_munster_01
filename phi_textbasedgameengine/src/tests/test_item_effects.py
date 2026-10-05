import pytest
from game.GameContext import GameContext
from game.GameError import GameError
from gameobjects.GameObject import GameObject
from gameobjects.Item import Item, tokenize
from tests.test_game_utils import MockGameObject, create_object, set_gameobject_id


def make_ctx(*objects):
	ctx = GameContext()
	for obj in objects:
		ctx.add(obj)
	return ctx

def make_item(name='potion', uses=1, effects=()):
	template = {'name': name, 'uses': uses, 'effects': list(effects)}
	return GameObject.load_from_template(template, Item)


def test_tokenize_basic():
	assert tokenize('add 5 player.health') == ['add', '5', 'player.health']

def test_tokenize_parenthesized_text():
	assert tokenize('say (hello there friend)') == ['say', 'hello there friend']

def test_tokenize_unmatched_close_paren():
	with pytest.raises(GameError):
		tokenize('add 5 player.health)')

def test_tokenize_unclosed_paren():
	with pytest.raises(GameError):
		tokenize('say (hello there')

def test_parse_effect_add_writes_back_state():
	player = create_object('player', 10)
	ctx = make_ctx(player)

	Item.parse_effect('add 5 player.prop')(ctx)

	assert player.prop == 15

def test_parse_effect_sub_writes_back_state():
	player = create_object('player', 10)
	ctx = make_ctx(player)

	Item.parse_effect('sub 3 player.prop')(ctx)

	assert player.prop == 7

def test_parse_effect_negative_value():
	player = create_object('player', 10)
	ctx = make_ctx(player)

	Item.parse_effect('add -4 player.prop')(ctx)

	assert player.prop == 6

def test_parse_effect_matches_simplified_name():
	obj = create_object('Health Potion', 1)
	ctx = make_ctx(obj)

	Item.parse_effect('add 1 health potion.prop')(ctx)

	assert obj.prop == 2

def test_parse_effect_all_selector():
	objects = [create_object('goblin', 5), create_object('goblin', 8)]
	ctx = make_ctx(*objects)

	Item.parse_effect('add 1 all goblin.prop')(ctx)

	assert [obj.prop for obj in objects] == [6, 9]

def test_parse_effect_min_selector():
	objects = [create_object('goblin', 5), create_object('goblin', 8)]
	ctx = make_ctx(*objects)

	Item.parse_effect('sub 1 min goblin.prop')(ctx)

	assert [obj.prop for obj in objects] == [4, 8]

def test_parse_effect_max_selector():
	objects = [create_object('goblin', 5), create_object('goblin', 8)]
	ctx = make_ctx(*objects)

	Item.parse_effect('sub 1 max goblin.prop')(ctx)

	assert [obj.prop for obj in objects] == [5, 7]

def test_parse_effect_any_selector():
	objects = [create_object('goblin', 5), create_object('goblin', 8)]
	ctx = make_ctx(*objects)

	Item.parse_effect('sub 1 any goblin.prop')(ctx)

	assert sorted(obj.prop for obj in objects) == [4, 8]

def test_parse_effect_say_sends_message():
	ctx = make_ctx()

	Item.parse_effect('say (Hello There, Friend!)')(ctx)

	assert ctx.messages == ['Hello There, Friend!']

def test_parse_effect_destroy_removes_object():
	obj = create_object('chest', None)
	ctx = make_ctx(obj)

	Item.parse_effect('destroy chest')(ctx)

	assert ctx.get_by_id(obj.id) is None

def test_parse_effect_spawn_adds_object():
	ctx = GameContext({'goblin': (MockGameObject, {'name': 'Goblin'})})

	Item.parse_effect('spawn goblin')(ctx)

	spawned = ctx.get_by_name('Goblin')
	assert len(spawned) == 1

def test_parse_effect_use_uses_object():
	item = make_item('scroll', uses=1, effects=['say (poof)'])
	ctx = make_ctx(item)

	Item.parse_effect('use scroll')(ctx)

	assert item.uses == 0
	assert ctx.get_by_id(item.id) is None
	assert ctx.messages == ['poof']

def test_parse_effect_unknown_object_raises():
	ctx = make_ctx()

	with pytest.raises(GameError) as errinfo:
		Item.parse_effect('add 5 ghost.health')(ctx)

	assert 'Unknown object "ghost"' in str(errinfo.value)

def test_parse_effect_unknown_property_raises():
	player = create_object('player', 10)
	ctx = make_ctx(player)

	with pytest.raises(GameError) as errinfo:
		Item.parse_effect('add 5 player.mana')(ctx)

	assert 'no property "mana"' in str(errinfo.value)

def test_parse_effect_unknown_spawn_raises():
	ctx = make_ctx()

	with pytest.raises(GameError) as errinfo:
		Item.parse_effect('spawn dragon')(ctx)

	assert 'Cannot spawn unknown object "dragon"' in str(errinfo.value)

def test_parse_effect_invalid_modifier_raises():
	with pytest.raises(GameError) as errinfo:
		Item.parse_effect('frobnicate 3 player.health')

	assert 'Invalid modifier "frobnicate"' in str(errinfo.value)

def test_parse_effect_missing_target_raises():
	with pytest.raises(GameError):
		Item.parse_effect('add 5')

def test_parse_effect_extra_tokens_raise():
	player = create_object('player', 10)
	ctx = make_ctx(player)

	with pytest.raises(GameError):
		Item.parse_effect('add 5 player.prop extra')(ctx)

def test_parse_effect_modify_without_property_raises():
	player = create_object('player', 10)
	ctx = make_ctx(player)

	with pytest.raises(GameError) as errinfo:
		Item.parse_effect('add 5 player')(ctx)

	assert 'a property is required' in str(errinfo.value)

def test_parse_effect_empty_raises():
	with pytest.raises(GameError):
		Item.parse_effect('   ')

def test_item_template_parses_effects():
	item = make_item('potion', uses=1, effects=['say (hi)', 'add 1 player.prop'])

	assert len(item.effects) == 2
	assert all(callable(effect) for effect in item.effects)

def test_item_template_invalid_effect_raises():
	template = {'name': 'bad', 'uses': 1, 'effects': ['frobnicate everything']}

	with pytest.raises(GameError):
		GameObject.load_from_template(template, Item)

def test_item_use_decrements_uses_and_applies_effects():
	player = create_object('player', 10)
	item = make_item('potion', uses=2, effects=['add 5 player.prop'])
	ctx = make_ctx(player, item)

	item.use(ctx)

	assert item.uses == 1
	assert player.prop == 15
	assert ctx.get_by_id(item.id) is item

def test_item_use_destroys_at_zero_uses():
	player = create_object('player', 10)
	item = make_item('potion', uses=1, effects=['add 5 player.prop'])
	ctx = make_ctx(player, item)

	item.use(ctx)

	assert item.uses == 0
	assert ctx.get_by_id(item.id) is None
	assert player.prop == 15
