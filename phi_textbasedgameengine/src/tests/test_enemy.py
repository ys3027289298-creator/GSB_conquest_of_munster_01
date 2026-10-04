import pytest
from game.GameError import GameError
from gameobjects.Enemy import Enemy
from tests.test_game_utils import set_gameobject_id


def test_enemy_instantiation():
    set_gameobject_id(100)
    enemy = Enemy()
    assert enemy.id == 100
    assert enemy.name is None


def test_enemy_load_from_template_range_values():
    enemy = Enemy.load_from_template({
        'name': 'dragon',
        'health': {'min': 10, 'max': 20},
        'defence': {'min': 1, 'max': 2},
        'attack': {'min': 3, 'max': 4},
        'xp': {'min': 50, 'max': 60},
    }, Enemy)
    assert enemy.name == 'dragon'
    assert enemy.health.min == 10
    assert enemy.health.max == 20
    assert enemy.xp.min == 50


def test_enemy_load_from_template_scalar_values():
    enemy = Enemy.load_from_template({
        'name': 'slime',
        'health': 5,
        'defence': 1,
        'attack': 2,
        'xp': 3,
    }, Enemy)
    assert enemy.health.min == 5
    assert enemy.health.max == 5
    assert enemy.defence.min == enemy.defence.max == 1


def test_enemy_load_missing_required_raises():
    with pytest.raises(AttributeError):
        Enemy.load_from_template({
            'name': 'incomplete',
            'defence': 1,
            'attack': 2,
            'xp': 3,
        }, Enemy)


def test_enemy_load_bad_value_raises_gameerror():
    with pytest.raises(GameError):
        Enemy.load_from_template({
            'name': 'broken',
            'health': 'not_a_number',
            'defence': 1,
            'attack': 2,
            'xp': 3,
        }, Enemy)


def test_enemy_clone_has_new_id():
    enemy = Enemy.load_from_template({
        'name': 'rat',
        'health': 2,
        'defence': 0,
        'attack': 1,
        'xp': 1,
    }, Enemy)
    clone = enemy.clone()
    assert clone.id != enemy.id
    assert clone.name == 'rat'
    assert clone.health == enemy.health
    clone.name = 'changed'
    assert enemy.name == 'rat'
