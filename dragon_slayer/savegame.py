"""Save/load support so progress survives exiting and restarting."""

import json
import os

DEFAULT_SAVE_PATH = os.path.join(os.path.dirname(__file__), "savegame.json")


def save_game(player, stage, path=DEFAULT_SAVE_PATH):
    data = {
        "name": player.name,
        "weapon": type(player).__name__,
        "health": player.health,
        "mana": player.mana,
        "potions": player.potions,
        "has_dragon_ring": player.has_dragon_ring,
        "is_alive": player.is_alive,
        "inventory": dict(player.inventory),
        "training_reward_claimed": player.training_reward_claimed,
        "stage": stage,
    }
    with open(path, "w") as save_file:
        json.dump(data, save_file)
    return data


def has_saved_game(path=DEFAULT_SAVE_PATH):
    return os.path.exists(path)


def load_game(path=DEFAULT_SAVE_PATH):
    """Return (player, stage) from a save file, or None when no save exists."""
    from weapons.staff import Staff
    from weapons.bow import Bow
    from weapons.shield import Shield
    from weapons.spear import Spear

    if not has_saved_game(path):
        return None
    with open(path) as save_file:
        data = json.load(save_file)
    weapon_classes = {
        "Staff": Staff,
        "Bow": Bow,
        "Shield": Shield,
        "Spear": Spear,
    }
    player = weapon_classes[data["weapon"]](data["name"])
    player.health = data["health"]
    player.mana = data["mana"]
    player.potions = data["potions"]
    player.has_dragon_ring = data["has_dragon_ring"]
    player.is_alive = data["is_alive"]
    player.inventory = dict(data.get("inventory", {}))
    player.training_reward_claimed = data.get("training_reward_claimed", False)
    return player, data["stage"]


def clear_save(path=DEFAULT_SAVE_PATH):
    if has_saved_game(path):
        os.remove(path)
