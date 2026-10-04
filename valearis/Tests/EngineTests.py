from unittest.case import TestCase
from Area import Area
from Item import Item
from Engine import (
    Game, Event, EmptyInputError, UnknownCommandError, UnknownAreaError,
    AreaNotAdjacentError, ItemNotFoundError, DuplicateItemError,
    EventAlreadyFiredError,
)
from Story import Story, NarrativeNode


def buildWorld():
    hall = Area('hall', 'a hall', 'a long hall')
    garden = Area('garden', 'a garden')
    key = Item('key', 'a rusty key')
    stone = Item('stone', 'a smooth stone')
    garden.items.add(key)
    hall.items.add(stone)
    hall.addAdjacent(garden)
    game = Game()
    game.addArea(hall)
    game.addArea(garden)
    return game, hall, garden, key, stone


class Item_dedup(TestCase):

    def test_equalItemsHaveSameHash(self):
        self.assertEqual(Item('key', 'desc'), Item('key', 'desc'))
        self.assertEqual(hash(Item('key', 'desc')), hash(Item('key', 'desc')))

    def test_sameItemAddedTwiceStaysOne(self):
        area = Area('area', '')
        item = Item('thing')
        area.items.add(item)
        area.items.add(item)
        self.assertEqual(area.items.__len__(), 1)

    def test_distinctButEqualItemsDedup(self):
        area = Area('area', '')
        area.items.add(Item('thing', 'same'))
        area.items.add(Item('thing', 'same'))
        self.assertEqual(area.items.__len__(), 1)

    def test_differentDescriptionsAreDifferentItems(self):
        area = Area('area', '')
        area.items.add(Item('thing', 'one'))
        area.items.add(Item('thing', 'two'))
        self.assertEqual(area.items.__len__(), 2)


class AreaSwitching(TestCase):

    def test_stateSurvivesSwitchingAwayAndBack(self):
        game, hall, garden, key, stone = buildWorld()
        game.move('garden')
        game.move('hall')
        game.move('garden')
        self.assertEqual(game.currentArea, garden)
        self.assertEqual(garden.items, {key})
        self.assertEqual(hall.items, {stone})

    def test_carriedItemsTravelWithPlayer(self):
        game, hall, garden, key, stone = buildWorld()
        game.move('garden')
        game.take('key')
        game.move('hall')
        self.assertEqual(set(game.inventory), {'key'})
        self.assertEqual(garden.items, set())

    def test_failedMoveKeepsCurrentArea(self):
        game, hall, garden, key, stone = buildWorld()
        attic = Area('attic', 'an attic')
        game.addArea(attic)
        self.assertRaises(AreaNotAdjacentError, game.move, 'attic')
        self.assertEqual(game.currentArea, hall)

    def test_unknownAreaRaises(self):
        game = Game()
        self.assertRaises(UnknownAreaError, game.move, 'nowhere')

    def test_duplicateAreaNameRaises(self):
        game = Game()
        game.addArea(Area('same', ''))
        self.assertRaises(Exception, game.addArea, Area('same', ''))


class TakeDrop(TestCase):

    def test_takeMovesItemOutOfArea(self):
        game, hall, garden, key, stone = buildWorld()
        game.move('garden')
        game.take('key')
        self.assertEqual(garden.items, set())
        self.assertEqual(set(game.inventory), {'key'})

    def test_takeMissingItemRaises(self):
        game, hall, garden, key, stone = buildWorld()
        self.assertRaises(ItemNotFoundError, game.take, 'key')

    def test_dropPutsItemBack(self):
        game, hall, garden, key, stone = buildWorld()
        game.move('garden')
        game.take('key')
        game.move('hall')
        game.drop('key')
        self.assertEqual(hall.items, {stone, key})
        self.assertEqual(game.inventory, {})

    def test_dropDuplicateNamedItemRaisesAndKeepsState(self):
        game, hall, garden, key, stone = buildWorld()
        game.move('garden')
        game.take('key')
        game.move('hall')
        hall.items.add(Item('key', 'a different key'))
        self.assertRaises(DuplicateItemError, game.drop, 'key')
        self.assertEqual(set(game.inventory), {'key'})
        self.assertEqual(hall.items, {stone, Item('key', 'a different key')})

    def test_dropMissingItemRaises(self):
        game = Game()
        game.addArea(Area('hall', ''))
        self.assertRaises(ItemNotFoundError, game.drop, 'key')


class EmptyAndUnknownInput(TestCase):

    def test_noneInputRaises(self):
        game, _, _, _, _ = buildWorld()
        self.assertRaises(EmptyInputError, game.handle, None)

    def test_emptyStringInputRaises(self):
        game, _, _, _, _ = buildWorld()
        self.assertRaises(EmptyInputError, game.handle, '')

    def test_whitespaceInputRaises(self):
        game, _, _, _, _ = buildWorld()
        self.assertRaises(EmptyInputError, game.handle, '   ')

    def test_commandWithoutArgumentRaises(self):
        game, _, _, _, _ = buildWorld()
        self.assertRaises(EmptyInputError, game.handle, 'go')
        self.assertRaises(EmptyInputError, game.handle, 'take   ')
        self.assertRaises(EmptyInputError, game.handle, 'drop')

    def test_unknownCommandRaises(self):
        game, _, _, _, _ = buildWorld()
        self.assertRaises(UnknownCommandError, game.handle, 'dance')


class MissingFields(TestCase):

    def test_eventWithoutNameRaises(self):
        self.assertRaises(ValueError, Event, None)
        self.assertRaises(ValueError, Event, '')

    def test_fromDictRejectsNonDict(self):
        self.assertRaises(ValueError, Game.from_dict, [])

    def test_fromDictMissingTopLevelFieldRaises(self):
        data = {'current_area': None, 'areas': {}, 'inventory': []}
        self.assertRaises(ValueError, Game.from_dict, data)

    def test_fromDictMissingAreaFieldRaises(self):
        data = {
            'current_area': 'a',
            'areas': {'a': {'items': [], 'adjacents': []}},
            'inventory': [],
            'fired_events': [],
        }
        self.assertRaises(ValueError, Game.from_dict, data)

    def test_fromDictMissingItemNameRaises(self):
        data = {
            'current_area': 'a',
            'areas': {'a': {
                'short_description': '',
                'items': [{'description': 'd'}],
                'adjacents': [],
            }},
            'inventory': [],
            'fired_events': [],
        }
        self.assertRaises(ValueError, Game.from_dict, data)


class Events(TestCase):

    def test_eventFiresOnce(self):
        game = Game()
        calls = []
        game.addEvent(Event('bell', lambda g: calls.append(1)))
        game.triggerEvent('bell')
        self.assertRaises(EventAlreadyFiredError, game.triggerEvent, 'bell')
        self.assertEqual(len(calls), 1)

    def test_unknownEventRaises(self):
        game = Game()
        self.assertRaises(Exception, game.triggerEvent, 'bell')

    def test_eventStateSurvivesReload(self):
        game = Game()
        game.addArea(Area('a', ''))
        game.addEvent(Event('bell'))
        game.triggerEvent('bell')
        reloaded = Game.from_dict(game.to_dict())
        self.assertTrue(reloaded.eventFired('bell'))
        self.assertRaises(EventAlreadyFiredError, reloaded.triggerEvent, 'bell')


class ReloadConsistency(TestCase):

    def test_areasItemsInventorySurviveReload(self):
        game, hall, garden, key, stone = buildWorld()
        game.move('garden')
        game.take('key')
        game.move('hall')
        game.addEvent(Event('bell'))
        game.triggerEvent('bell')
        snapshot = game.to_dict()
        reloaded = Game.from_dict(snapshot)
        self.assertEqual(reloaded.to_dict(), snapshot)
        self.assertEqual(reloaded.currentArea.name, 'hall')
        self.assertEqual(reloaded.area('garden').items, set())
        self.assertEqual(set(game.inventory), {'key'})
        self.assertEqual(set(reloaded.inventory), {'key'})
        self.assertEqual(reloaded.area('hall').items, {stone})
        self.assertTrue(reloaded.area('hall') in reloaded.area('garden').adjacents)
        self.assertTrue(reloaded.area('garden') in reloaded.area('hall').adjacents)

    def test_reloadThenSwitchKeepsStateConsistent(self):
        game, hall, garden, key, stone = buildWorld()
        game.move('garden')
        game.take('key')
        reloaded = Game.from_dict(game.to_dict())
        reloaded.move('hall')
        reloaded.drop('key')
        reloaded.move('garden')
        self.assertEqual(reloaded.area('hall').items, {stone, key})
        self.assertEqual(reloaded.area('garden').items, set())
        self.assertEqual(reloaded.inventory, {})

    def test_storyStateSurvivesReload(self):
        node_a = NarrativeNode('a', 'first')
        node_b = NarrativeNode('b', 'second')
        node_a.addChoice('next', node_b)
        game = Game()
        game.addArea(Area('a', ''))
        game.attachStory(Story(node_a))
        game.story.choose('next')
        snapshot = game.to_dict()

        node_a2 = NarrativeNode('a', 'first')
        node_b2 = NarrativeNode('b', 'second')
        node_a2.addChoice('next', node_b2)
        reloaded = Game.from_dict(snapshot)
        reloaded.attachStory(Story(node_a2))
        self.assertEqual(reloaded.story.current, node_b2)
