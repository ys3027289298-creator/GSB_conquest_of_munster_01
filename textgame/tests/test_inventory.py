import unittest

import tests  # noqa: F401  sets up sys.path
from inventory import Inventory


class InventoryTest(unittest.TestCase):

    def test_instances_do_not_share_slots(self):
        bag_a = Inventory()
        bag_b = Inventory()
        bag_a.slots['wood'] += 5
        self.assertEqual(bag_b.slots['wood'], 1)
        self.assertEqual(bag_a.slots['wood'], 6)

    def test_default_contents(self):
        inv = Inventory()
        self.assertEqual(inv.slots['wood'], 1)
        self.assertEqual(inv.slots['stone'], 0)
        self.assertEqual(inv.slots['stone sword'], 0)

    def test_add_known_item(self):
        inv = Inventory()
        inv.add('stone', 3)
        self.assertEqual(inv.slots['stone'], 3)

    def test_add_unknown_item_rejected(self):
        inv = Inventory()
        with self.assertRaises(KeyError):
            inv.add('jetpack')
        self.assertNotIn('jetpack', inv.slots)

    def test_remove_never_goes_negative(self):
        inv = Inventory()
        inv.remove('wood', 99)
        self.assertEqual(inv.slots['wood'], 0)

    def test_bag_lists_items(self):
        inv = Inventory()
        self.assertEqual(inv.bag(), ' ')


if __name__ == '__main__':
    unittest.main()
