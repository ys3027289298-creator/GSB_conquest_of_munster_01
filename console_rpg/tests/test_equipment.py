"""Bugs 3 (duplicated equipment bonus) and 5 (pickup despite full bag)."""
import builtins
import io
import contextlib
import itertools
import unittest
import unittest.mock

from tests.helpers import make_game, make_game_main, quiet

from game.data.characters.equipment.Items import Item
from game.data.characters.NPC import NPC


class TestWeaponEquipping(unittest.TestCase):
    def test_default_weapons_arms_exactly_one(self):
        game_main = make_game_main(5)
        player = game_main.game_now.player
        player.Eq1.add_element("Axe")
        player.Eq1.add_element("Hammer")
        # nothing equipped, as happens after the current weapon is sold/handed in
        for item in player.Eq1.elements:
            item.is_weapon = 1
        quiet(game_main.set_weapon_default)
        active = [item.name for item in player.Eq1.elements
                  if item.is_weapon == 2]
        self.assertEqual(len(active), 1, active)

    def test_change_weapon_keeps_single_active_weapon(self):
        game_main = make_game_main(5)
        player = game_main.game_now.player
        player.Eq1.add_element("Axe")
        answers = itertools.chain(iter(["2"]), iter(["0"]))
        with unittest.mock.patch.object(builtins, "input",
                                        lambda *a, **k: next(answers)):
            quiet(game_main.change_weapon)
        active = [item for item in player.Eq1.elements
                  if item.is_weapon == 2]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].name, "Axe")
        weapons = [item for item in player.Eq1.elements
                   if item.is_weapon in (1, 2)]
        self.assertEqual(len([w for w in weapons if w.is_weapon == 2]), 1)

    def test_battle_uses_the_selected_weapon_damage(self):
        game_main = make_game_main(5)
        player = game_main.game_now.player
        player.Eq1.add_element("Silver Claymore")  # damage 20
        answers = itertools.chain(iter(["2"]), iter(["0"]))
        with unittest.mock.patch.object(builtins, "input",
                                        lambda *a, **k: next(answers)):
            quiet(game_main.change_weapon)
        active = [item for item in player.Eq1.elements
                  if item.is_weapon == 2]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].name, "Silver Claymore")
        self.assertEqual(active[0].damage, 20)


class TestInventoryCapacity(unittest.TestCase):
    def test_add_element_refuses_when_full(self):
        game = make_game(0)
        player = game.player
        player.Eq1.capacity = len(player.Eq1.elements)
        self.assertFalse(player.Eq1.add_element("Apple"))
        self.assertEqual(len(player.Eq1.elements), player.Eq1.capacity)

    def test_collect_leaves_item_on_ground_when_full(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        player = game.player
        player.Eq1.capacity = len(player.Eq1.elements)
        game.items_map[30] = [Item("Apple")]
        quiet(game_main.collect_items, 30)
        self.assertEqual([item.name for item in game.items_map[30]], ["Apple"])
        self.assertEqual(len(player.Eq1.elements), player.Eq1.capacity)
        self.assertNotIn("Apple", player.Eq1.items_names())

    def test_collect_multi_item_pile_stops_at_capacity(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        player = game.player
        player.Eq1.capacity = len(player.Eq1.elements) + 2
        game.items_map[30] = [Item("Apple"), Item("Herb"), Item("Reed")]
        quiet(game_main.collect_items, 30)
        self.assertEqual([item.name for item in game.items_map[30]], ["Reed"])
        self.assertEqual(len(player.Eq1.elements), player.Eq1.capacity)

    def test_collect_with_space_takes_everything(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        game.items_map[30] = [Item("Apple"), Item("Herb")]
        quiet(game_main.collect_items, 30)
        self.assertEqual(game.items_map[30], [])

    def test_cannot_buy_when_inventory_full(self):
        game_main = make_game_main(0)
        game = game_main.game_now
        player = game.player
        trader = NPC("Merchant", 88)
        player.Eq1.capacity = len(player.Eq1.elements)
        gold_before = player.Eq1.gold
        answers = iter(["1", "0"])
        with unittest.mock.patch.object(builtins, "input",
                                        lambda *a, **k: next(answers)):
            quiet(game_main.buying_mode, trader)
        self.assertEqual(player.Eq1.gold, gold_before)
        self.assertEqual(len(player.Eq1.elements), player.Eq1.capacity)
        self.assertIn("Sword", trader.Equipment.items_names())


if __name__ == "__main__":
    unittest.main()
