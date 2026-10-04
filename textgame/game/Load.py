import json


def save_game(controls, path):
    state = {
        'room': controls.loc.id,
        'player': {
            'name': controls.player.name,
            'hp': controls.player.hp,
            'right_hand': controls.player.right_hand,
            'left_hand': controls.player.left_hand,
        },
        'inventory': dict(controls.inventory.slots),
    }
    with open(path, 'w') as f:
        json.dump(state, f, indent=2)
    return state


def load_game(controls, path):
    with open(path, 'r') as f:
        state = json.load(f)
    restore(controls, state)
    return state


def restore(controls, state):
    from room import get_room
    controls.loc = get_room(state['room'])
    controls.pos()
    player = state.get('player', {})
    controls.player.name = player.get('name', '')
    controls.player.hp = player.get('hp', controls.player.MAX_HP)
    controls.player.right_hand = player.get('right_hand')
    controls.player.left_hand = player.get('left_hand')
    for item, count in state.get('inventory', {}).items():
        if item in controls.inventory.slots:
            controls.inventory.slots[item] = count
