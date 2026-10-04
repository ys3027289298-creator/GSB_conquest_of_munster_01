import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'game'))

from inventory import Inventory
from itemlib import Items, ITEM_IDS, ITEM_NAMES


class TestInventory(unittest.TestCase):

    def test_slots_are_not_shared_between_instances(self):
        first = Inventory()
        second = Inventory()
        first.add_item('wood', 3)
        self.assertEqual(first.slots['wood'], 3)
        self.assertEqual(second.slots['wood'], 0)
        self.assertIsNot(first.slots, second.slots)

    def test_add_item_stacks_quantity(self):
        inv = Inventory()
        inv.add_item('wood')
        inv.add_item('wood', 2)
        self.assertEqual(inv.slots['wood'], 3)

    def test_add_unknown_item_raises(self):
        inv = Inventory()
        with self.assertRaises(KeyError):
            inv.add_item('dragon')

    def test_has_item_unknown_returns_false(self):
        inv = Inventory()
        self.assertFalse(inv.has_item('dragon'))
        self.assertFalse(inv.has_item('wood'))
        inv.add_item('wood')
        self.assertTrue(inv.has_item('wood'))

    def test_take_item(self):
        inv = Inventory()
        inv.add_item('stone', 2)
        self.assertEqual(inv.take_item('stone'), 1)
        with self.assertRaises(KeyError):
            inv.take_item('dirt')
        with self.assertRaises(ValueError):
            inv.take_item('stone', 5)

    def test_all_catalog_items_have_slots(self):
        inv = Inventory()
        for name in ITEM_NAMES:
            self.assertIn(name, inv.slots)


class TestItemLib(unittest.TestCase):

    def test_item_id_lookup(self):
        self.assertEqual(Items.item_id(1), 'wood')
        self.assertEqual(Items.item_id(9), 'stone sword')
        self.assertIsNone(Items.item_id(999))

    def test_catalog_matches_names(self):
        self.assertEqual(sorted(ITEM_IDS.values()), sorted(ITEM_NAMES))

    def test_unknown_item_rejected(self):
        with self.assertRaises(KeyError):
            Items(item='dragon')
        item = Items(item='wooden axe', durability=10)
        self.assertEqual(item.item, 'wooden axe')


if __name__ == '__main__':
    unittest.main()
