"""Reproduce the six known bugs in textgame. Run: python3 reproduce_bugs.py"""
import io
import os
import sys
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game'))

failures = []


def check(title, fn):
    try:
        detail = fn()
        if detail:
            failures.append((title, detail))
            print('FAIL  {} -> {}'.format(title, detail))
        else:
            print('PASS  {}'.format(title))
    except Exception as exc:
        failures.append((title, '{}: {}'.format(type(exc).__name__, exc)))
        print('FAIL  {} -> {}: {}'.format(title, type(exc).__name__, exc))


def new_controls():
    from main import Controls
    with contextlib.redirect_stdout(io.StringIO()):
        return Controls()


# 1. inventory duplicate add: class-level slots dict is shared by instances
def bug_inventory_shared():
    from inventory import Inventory
    bag_a, bag_b = Inventory(), Inventory()
    bag_a.slots['wood'] += 5
    if bag_b.slots['wood'] != 1:
        return 'adding to one inventory leaked into another (wood={})'.format(
            bag_b.slots['wood'])
check('1. inventory duplicate add / shared slots', bug_inventory_shared)

# 2. item does not exist: do_get must reject it without crashing
def bug_unknown_item():
    from inventory import Inventory
    inv = Inventory()
    if inv.slots.get('jetpack') is not None:
        return 'unknown item should not be in the bag'
    c = new_controls()
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            c.do_get('jetpack')
    except KeyError:
        return 'do_get crashed with KeyError on unknown item'
    if 'do not have' not in out.getvalue():
        return 'do_get did not report the missing item'
check('2. unknown item lookup', bug_unknown_item)

# 3. room switch state not updated: position never stored, do_e moves twice
def bug_room_state():
    c = new_controls()
    with contextlib.redirect_stdout(io.StringIO()):
        c.move('n')
    if not hasattr(c, 'position') or c.position != c.loc.name:
        return 'position not updated after room switch (position=%r, loc=%r)' % (
            getattr(c, 'position', None), c.loc.name)
    calls = []
    original = c.move
    def counting_move(direction):
        calls.append(direction)
        return original(direction)
    c.move = counting_move
    with contextlib.redirect_stdout(io.StringIO()):
        c.do_e('')
    if len(calls) != 1:
        return 'do_e triggered {} move call(s): {}'.format(len(calls), calls)
check('3. room switch updates state', bug_room_state)

# 4. monster attribute out of bounds: missing key silently returns key name
def bug_monster_missing():
    from Creatures import Monster
    try:
        Monster(name='kevin', level=20, height=45, attack=20)['health']
    except KeyError:
        return None
    return 'missing monster attribute did not raise KeyError' 
check('4. monster missing attribute rejected', bug_monster_missing)

# 5. load failure: Load module cannot save/restore game state
def bug_load():
    import Load
    c = new_controls()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'repro_save.json')
    if not hasattr(Load, 'save_game') or not hasattr(Load, 'load_game'):
        return 'Load module has no save_game/load_game implementation'
    with contextlib.redirect_stdout(io.StringIO()):
        Load.save_game(c, path)
        c.move('n')
        Load.load_game(c, path)
    if c.loc.id != 'intro':
        return 'room not restored after load (got %r)' % c.loc.id
check('5. save/load restores game state', bug_load)

# 6. player dead but can still move
def bug_dead_player():
    from player import Player
    p = Player()
    if not hasattr(p, 'alive') or not hasattr(p, 'take_damage'):
        return 'Player has no alive/take_damage state'
    c = new_controls()
    c.Player.take_damage(c.Player.health)
    with contextlib.redirect_stdout(io.StringIO()) as out:
        c.move('n')
    if c.loc.id != 'intro':
        return 'dead player moved to %r' % c.loc.id
check('6. dead player cannot move', bug_dead_player)

print()
print('{} of 6 checks still failing'.format(len(failures)))
sys.exit(1 if failures else 0)
