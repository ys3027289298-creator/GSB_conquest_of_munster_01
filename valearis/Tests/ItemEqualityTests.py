from unittest import TestCase
from Area import Area
from Item import Item


class Item_equality(TestCase):

    def test_equal_items_compare_equal(self):
        self.assertEqual(Item('key', 'a key'), Item('key', 'a key'))

    def test_different_descriptions_compare_different(self):
        self.assertNotEqual(Item('key', 'a key'), Item('key', 'another key'))

    def test_duplicate_items_collapse_in_set(self):
        items = {Item('key', 'a key'), Item('key', 'a key')}

        self.assertEqual(items.__len__(), 1)

    def test_non_item_does_not_compare_equal(self):
        self.assertNotEqual(Item('key', 'a key'), 'key')


class Area_add_item(TestCase):

    def test_addItem_returns_true(self):
        area = Area('area', '')

        self.assertTrue(area.addItem(Item('key', 'a key')))

    def test_addItem_rejects_duplicate(self):
        area = Area('area', '')

        self.assertTrue(area.addItem(Item('key', 'a key')))
        self.assertFalse(area.addItem(Item('key', 'a key')))
        self.assertEqual(area.items.__len__(), 1)

    def test_addItem_rejects_none(self):
        area = Area('area', '')

        self.assertRaises(ValueError, area.addItem, None)

    def test_removeItem_returns_false_when_absent(self):
        area = Area('area', '')

        self.assertFalse(area.removeItem(Item('key', 'a key')))

    def test_removeItem_removes_once(self):
        area = Area('area', '')
        item = Item('key', 'a key')
        area.addItem(item)

        self.assertTrue(area.removeItem(item))
        self.assertEqual(area.items.__len__(), 0)
        self.assertRaises(ValueError, area.removeItem, None)
