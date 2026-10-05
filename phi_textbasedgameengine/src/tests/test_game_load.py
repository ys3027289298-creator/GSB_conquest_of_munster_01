import pytest
from game.Game import Game
from game.GameError import GameError
from gameobjects.Enemy import Enemy
from gameobjects.Item import Item


def write_game(directory, files):
	for relative, content in files.items():
		path = directory / relative
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(content)

VALID_GAME = {
	'enemies.yml': 'include:\n  - data/goblin.yml\n',
	'data/goblin.yml': (
		'name: Goblin\n'
		'health:\n  min: 4\n  max: 6\n'
		'defence: 2\n'
		'attack:\n  min: 1\n  max: 3\n'
		'xp: 10\n'
	),
	'rooms.yml': 'include:\n  - data/entrance.yml\n',
	'data/entrance.yml': 'name: Dungeon Entrance\n',
	'items.yml': 'include:\n  - data/potion.yml\n  - data/whistle.yml\n',
	'data/potion.yml': (
		'name: Health Potion\n'
		'description: heals you\n'
		'uses: 2\n'
		'effects:\n  - "say (You feel refreshed)"\n  - "add 5 player.health"\n'
	),
	'data/whistle.yml': (
		'name: Goblin Whistle\n'
		'uses: 1\n'
		'effects:\n  - "spawn goblin"\n'
	),
	'player.yml': 'name: Player\nhealth: 10\n'
}


def test_load_valid_game(tmp_path):
	write_game(tmp_path, VALID_GAME)

	game = Game.load_game(str(tmp_path))

	assert len(game.enemies) == 1
	enemy = game.enemies[0]
	assert isinstance(enemy, Enemy)
	assert enemy.name == 'Goblin'
	assert enemy.health.min == 4 and enemy.health.max == 6

	assert len(game.items) == 2
	for item in game.items:
		assert isinstance(item, Item)
		assert all(callable(effect) for effect in item.effects)

	assert {obj['name'] for obj in game.rooms} == {'Dungeon Entrance'}
	assert game.player[0]['name'] == 'Player'

	assert set(game.templates) == {'goblin', 'health potion', 'goblin whistle'}

def test_new_context_uses_game_templates(tmp_path):
	write_game(tmp_path, VALID_GAME)
	game = Game.load_game(str(tmp_path))

	ctx = game.new_context()
	spawned = ctx.spawn('goblin')

	assert spawned.name == 'Goblin'
	assert ctx.get_by_name('Goblin')[0] is spawned

def test_load_missing_directory_raises(tmp_path):
	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path / 'missing'))

	assert 'Could not find game directory' in str(errinfo.value)

def test_load_missing_required_yaml_raises(tmp_path):
	write_game(tmp_path, {key: value for key, value in VALID_GAME.items() if not key.startswith('enemies')})

	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path))

	assert "enemies" in str(errinfo.value)

def test_load_missing_required_field_raises(tmp_path):
	files = dict(VALID_GAME)
	files['data/goblin.yml'] = 'name: Goblin\ndefence: 2\nattack: 1\nxp: 10\n'
	write_game(tmp_path, files)

	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path))

	assert 'health' in str(errinfo.value)

def test_load_unexpected_field_raises(tmp_path):
	files = dict(VALID_GAME)
	files['data/goblin.yml'] = (
		'name: Goblin\nhealth: 5\ndefence: 2\nattack: 1\nxp: 10\nbogus: true\n'
	)
	write_game(tmp_path, files)

	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path))

	assert 'bogus' in str(errinfo.value)

def test_load_duplicate_names_raises(tmp_path):
	files = dict(VALID_GAME)
	files['enemies.yml'] = 'include:\n  - data/goblin.yml\n  - data/other_goblin.yml\n'
	files['data/other_goblin.yml'] = files['data/goblin.yml']
	write_game(tmp_path, files)

	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path))

	assert 'used multiple times' in str(errinfo.value)

def test_load_duplicate_name_across_categories_raises(tmp_path):
	files = dict(VALID_GAME)
	files['data/whistle.yml'] = (
		'name: Goblin\n'
		'uses: 1\n'
		'effects:\n  - "say (honk)"\n'
	)
	write_game(tmp_path, files)

	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path))

	assert '"goblin"' in str(errinfo.value)

def test_load_invalid_effect_raises(tmp_path):
	files = dict(VALID_GAME)
	files['data/potion.yml'] = (
		'name: Health Potion\n'
		'uses: 1\n'
		'effects:\n  - "frobnicate everything"\n'
	)
	write_game(tmp_path, files)

	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path))

	assert 'frobnicate' in str(errinfo.value)

def test_load_invalid_name_raises(tmp_path):
	files = dict(VALID_GAME)
	files['data/goblin.yml'] = files['data/goblin.yml'].replace('name: Goblin', 'name: !!!')
	write_game(tmp_path, files)

	with pytest.raises(GameError):
		Game.load_game(str(tmp_path))

def test_load_circular_include_raises(tmp_path):
	files = dict(VALID_GAME)
	files['enemies.yml'] = 'include:\n  - data/a.yml\n'
	files['data/a.yml'] = 'name: a\ninclude:\n  - b.yml\n'
	files['data/b.yml'] = 'name: b\ninclude:\n  - a.yml\n'
	write_game(tmp_path, files)

	with pytest.raises(GameError) as errinfo:
		Game.load_game(str(tmp_path))

	assert 'Circular include' in str(errinfo.value)
