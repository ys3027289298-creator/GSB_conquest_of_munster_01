"""Exactly one weapon may be equipped (bug #3): the duplicated is_weapon
state made several weapons 'in use' at once, so the bonus applied to
battles no longer matched the weapon shown to the player."""
import builtins
import unittest.mock

from tests.helpers import QuietTestCase, make_game, make_game_main


def equipped_names(game):
    return [item.name for item in game.player.Eq1.elements if item.is_weapon == 2]


class EquipmentStateTest(QuietTestCase):

    def setUp(self):
        super().setUp()
        self.game = make_game(0)
        self.game_main = make_game_main(self.game)
        self.game.player.Eq1.add_element("Axe")
        self.game.player.Eq1.add_element("Hammer")

    def test_player_starts_with_single_equipped_weapon(self):
        game = make_game(0)
        self.assertEqual(equipped_names(game), ["Sword"])

    def test_default_weapon_equips_only_first_one(self):
        for item in self.game.player.Eq1.elements:
            if item.is_weapon:
                item.is_weapon = 1
        self.game_main.set_weapon_default()
        self.assertEqual(len(equipped_names(self.game)), 1)
        self.game_main.set_weapon_default()  # idempotent
        self.assertEqual(len(equipped_names(self.game)), 1)

    def test_default_weapon_after_losing_equipped_one(self):
        # emulate the monk quest / selling taking the equipped Sword
        for index, item in enumerate(self.game.player.Eq1.elements):
            if item.name == "Sword":
                self.game.player.Eq1.remove_element(index)
                break
        self.game_main.set_weapon_default()
        self.assertEqual(len(equipped_names(self.game)), 1)

    def test_change_weapon_keeps_single_equipped_weapon(self):
        # Sword is equipped by default; weapons list order: Sword, Axe, Hammer
        with unittest.mock.patch.object(builtins, "input", return_value="2"):
            self.game_main.change_weapon()
        self.assertEqual(equipped_names(self.game), ["Axe"])
        # changing again to "1" (Sword) does not leave the Axe equipped
        with unittest.mock.patch.object(builtins, "input", return_value="1"):
            self.game_main.change_weapon()
        self.assertEqual(equipped_names(self.game), ["Sword"])

    def test_change_weapon_with_duplicate_names(self):
        self.game.player.Eq1.add_element("Sword")  # second Sword
        for item in self.game.player.Eq1.elements:
            if item.is_weapon:
                item.is_weapon = 1
        # equip an Axe first
        for item in self.game.player.Eq1.elements:
            if item.name == "Axe":
                item.is_weapon = 2
        # choosing "Sword" (a name that appears twice) equips only that one
        with unittest.mock.patch.object(builtins, "input", return_value="1"):
            self.game_main.change_weapon()
        self.assertEqual(len(equipped_names(self.game)), 1)
        self.assertEqual(equipped_names(self.game)[0], "Sword")
