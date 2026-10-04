from unittest import TestCase
from Area import Area
from Item import Item
from Narrative import Narrative, NarrativeNode


class Narrative_items(TestCase):

    def test_item_without_description_is_not_presented(self):
        area = Area('area', 'short')
        area.addItem(Item('key'))
        narrative = Narrative(area)

        self.assertEqual(narrative.items.__len__(), 0)
        self.assertEqual(narrative.presentationOfItems, None)

    def test_only_items_without_description_are_skipped(self):
        area = Area('area', 'short')
        area.addItem(Item('no description'))
        area.addItem(Item('described', 'an item.'))
        narrative = Narrative(area)

        self.assertEqual(narrative.items.__len__(), 1)
        self.assertTrue(narrative.items.__contains__('an item.'))


class NarrativeNode_walk(TestCase):

    def test_linear_nodes_walk_in_order(self):
        first = NarrativeNode('first')
        second = NarrativeNode('second')
        third = NarrativeNode('third')
        first.addNext(second)
        second.addNext(third)

        order = first.walk()

        self.assertEqual([node.text for node in order], ['first', 'second', 'third'])

    def test_diamond_graph_does_not_loop(self):
        first = NarrativeNode('first')
        middle_a = NarrativeNode('a')
        middle_b = NarrativeNode('b')
        last = NarrativeNode('last')
        first.addNext(middle_a)
        first.addNext(middle_b)
        middle_a.addNext(last)
        middle_b.addNext(last)

        order = first.walk()

        self.assertEqual([node.text for node in order], ['first', 'a', 'last', 'b'])

    def test_cycle_raises_error(self):
        first = NarrativeNode('first')
        second = NarrativeNode('second')
        first.addNext(second)
        second.addNext(first)

        self.assertRaises(ValueError, first.walk)

    def test_self_cycle_raises_error(self):
        node = NarrativeNode('node')
        node.addNext(node)

        self.assertRaises(ValueError, node.walk)

    def test_addNext_rejects_none_and_duplicate(self):
        node = NarrativeNode('node')
        other = NarrativeNode('other')

        self.assertRaises(ValueError, node.addNext, None)
        self.assertTrue(node.addNext(other))
        self.assertFalse(node.addNext(other))
        self.assertEqual(node.nextNodes.__len__(), 1)

    def test_node_requires_text(self):
        self.assertRaises(ValueError, NarrativeNode, None)
