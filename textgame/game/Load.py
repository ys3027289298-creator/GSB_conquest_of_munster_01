import json
import os

from room import get_room

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'savegame.json')


def save_game(controls, path=SAVE_FILE):
    state = {
        'room': controls.loc.id,
        'player': {
            'name': controls.Player.name,
            'health': controls.Player.health,
            'max_health': controls.Player.max_health,
            'alive': controls.Player.alive,
        },
        'inventory': dict(controls.inventory.slots),
    }
    with open(path, 'w') as f:
        json.dump(state, f, indent=2)
    return path


def load_game(controls, path=SAVE_FILE):
    if not os.path.exists(path):
        return False
    with open(path, 'r') as f:
        state = json.load(f)
    controls.loc = get_room(state['room'])
    controls.pos()
    player = state.get('player', {})
    controls.Player.name = player.get('name', '')
    controls.Player.max_health = player.get('max_health', 100)
    controls.Player.health = player.get('health', controls.Player.max_health)
    controls.Player.alive = player.get('alive', True)
    inventory = state.get('inventory', {})
    for item, count in inventory.items():
        if item in controls.inventory.slots:
            controls.inventory.slots[item] = count
    return True
