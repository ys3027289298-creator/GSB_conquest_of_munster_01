import json
import os

from weapons.staff import Staff
from weapons.bow import Bow
from weapons.shield import Shield
from weapons.spear import Spear

INTRO = "intro"
TRAINING = "training"
FISHING = "fishing"
BATTLE = "battle"
LOST = "lost"
WON = "won"

ORDER = [INTRO, TRAINING, FISHING, BATTLE, WON]

WEAPONS = {
    "Staff": Staff,
    "Bow": Bow,
    "Shield": Shield,
    "Spear": Spear,
}

DEFAULT_SAVE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "save_game.json")


def next_node(node):
    if node == LOST:
        return BATTLE
    index = ORDER.index(node)
    return ORDER[index + 1]


class GameState:
    def __init__(self, node=INTRO, player=None):
        self.node = node
        self.player = player

    @classmethod
    def new_game(cls, player):
        return cls(node=TRAINING, player=player)

    def advance(self):
        self.node = next_node(self.node)

    def to_dict(self):
        player = self.player
        data = {
            "node": self.node,
            "player": None,
        }
        if player is not None:
            data["player"] = {
                "name": player.name,
                "weapon": type(player).__name__,
                "health": player.health,
                "mana": player.mana,
                "potions": player.potions,
                "has_dragon_ring": player.has_dragon_ring,
            }
        return data

    @classmethod
    def from_dict(cls, data):
        state = cls(node=data.get("node", INTRO))
        player_data = data.get("player")
        if player_data:
            weapon_class = WEAPONS[player_data["weapon"]]
            player = weapon_class(player_data["name"])
            player.health = player_data["health"]
            player.mana = player_data["mana"]
            player.potions = player_data["potions"]
            player.has_dragon_ring = player_data["has_dragon_ring"]
            player.is_alive = player.health > 0
            state.player = player
        return state

    def save(self, path=None):
        path = path if path is not None else DEFAULT_SAVE_PATH
        with open(path, "w") as save_file:
            json.dump(self.to_dict(), save_file)

    @classmethod
    def load(cls, path=None):
        path = path if path is not None else DEFAULT_SAVE_PATH
        with open(path) as save_file:
            return cls.from_dict(json.load(save_file))

    @classmethod
    def exists(cls, path=None):
        path = path if path is not None else DEFAULT_SAVE_PATH
        return os.path.exists(path)

    @classmethod
    def clear(cls, path=None):
        path = path if path is not None else DEFAULT_SAVE_PATH
        if os.path.exists(path):
            os.remove(path)
