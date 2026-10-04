from unittest import TestCase
from Area import Area
from Item import Item
from Game import Game


def buildWorld():
    hall = Area('hall', 'a hall')
    kitchen = Area('kitchen', 'a kitchen')
    garden = Area('garden', 'a garden')
    hall.addAdjacent(kitchen)
    kitchen.addAdjacent(garden)

    hall_key = Item('key', 'a rusty key')
    kitchen_apple = Item('apple', 'a red apple')
    hall.addItem(hall_key)
    kitchen.addItem(kitchen_apple)

    return (hall, kitchen, garden, hall_key, kitchen_apple)


class Game_start(TestCase):

    def test_requires_start_area(self):
        self.assertRaises(ValueError, Game, None)

    def test_starts_in_given_area(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertIs(game.currentArea, hall)


class Game_movement(TestCase):

    def test_moves_to_adjacent_area(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        game.moveTo(kitchen)

        self.assertIs(game.currentArea, kitchen)

    def test_moves_to_adjacent_area_by_name(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        game.moveTo('kitchen')

        self.assertIs(game.currentArea, kitchen)

    def test_cannot_move_to_non_adjacent_area(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertRaises(ValueError, game.moveTo, garden)
        self.assertIs(game.currentArea, hall)

    def test_cannot_move_to_unknown_name(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertRaises(ValueError, game.moveTo, 'nowhere')

    def test_cannot_move_with_empty_name(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertRaises(ValueError, game.moveTo, '')
        self.assertRaises(ValueError, game.moveTo, '   ')
        self.assertIs(game.currentArea, hall)

    def test_area_state_survives_switching(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        game.moveTo(kitchen)
        game.moveTo(hall)

        self.assertEqual(hall.items, {hall_key})
        self.assertEqual(kitchen.items, {kitchen_apple})


class Game_items(TestCase):

    def test_take_moves_item_into_inventory(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertTrue(game.take(hall_key))
        self.assertEqual(game.inventory, {hall_key})
        self.assertEqual(hall.items.__len__(), 0)

    def test_take_missing_item_returns_false(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)
        stray = Item('sword', 'a sword')

        self.assertFalse(game.take(stray))
        self.assertEqual(game.inventory.__len__(), 0)

    def test_cannot_take_same_item_twice(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertTrue(game.take(hall_key))
        self.assertFalse(game.take(hall_key))
        self.assertEqual(game.inventory.__len__(), 1)

    def test_cannot_take_duplicate_items_from_area(self):
        hall = Area('hall', 'a hall')
        hall.addItem(Item('key', 'a rusty key'))
        hall.addItem(Item('key', 'a rusty key'))
        game = Game(hall)

        game.take(Item('key', 'a rusty key'))

        self.assertEqual(hall.items.__len__(), 0)
        self.assertEqual(game.inventory.__len__(), 1)

    def test_drop_returns_item_to_current_area(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)
        game.take(hall_key)

        game.moveTo(kitchen)
        self.assertTrue(game.drop(hall_key))

        self.assertEqual(kitchen.items, {hall_key, kitchen_apple})
        self.assertEqual(game.inventory.__len__(), 0)

    def test_drop_missing_item_returns_false(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertFalse(game.drop(hall_key))

    def test_take_and_drop_reject_none(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)

        self.assertRaises(ValueError, game.take, None)
        self.assertRaises(ValueError, game.drop, None)


class Game_persistence(TestCase):

    def test_save_and_load_keeps_area_and_inventory(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)
        game.take(hall_key)
        game.moveTo(kitchen)

        save_data = game.save()
        loaded = Game.load(save_data, [hall, kitchen, garden])

        self.assertIs(loaded.currentArea, kitchen)
        self.assertEqual(loaded.inventory, {hall_key})
        self.assertEqual(hall.items.__len__(), 0)

    def test_loaded_game_keeps_state_after_switching(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        game = Game(hall)
        game.take(hall_key)
        game.moveTo(kitchen)

        loaded = Game.load(game.save(), [hall, kitchen, garden])
        loaded.moveTo(hall)

        self.assertIs(loaded.currentArea, hall)
        self.assertEqual(loaded.inventory, {hall_key})
        self.assertEqual(hall.items, set())
        self.assertEqual(kitchen.items, {kitchen_apple})

    def test_load_rejects_missing_current_area(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()

        self.assertRaises(ValueError, Game.load, {'inventory': []}, [hall, kitchen])

    def test_load_rejects_missing_inventory(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()

        self.assertRaises(ValueError, Game.load, {'current_area': 'hall'}, [hall, kitchen])

    def test_load_rejects_empty_current_area(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()

        self.assertRaises(ValueError, Game.load, {'current_area': '   ', 'inventory': []}, [hall, kitchen])

    def test_load_rejects_unknown_area(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        save_data = {'current_area': 'dungeon', 'inventory': []}

        self.assertRaises(ValueError, Game.load, save_data, [hall, kitchen])

    def test_load_rejects_item_with_missing_name(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        save_data = {'current_area': 'hall', 'inventory': [{'description': 'nameless'}]}

        self.assertRaises(ValueError, Game.load, save_data, [hall, kitchen])

    def test_load_rejects_item_with_empty_name(self):
        hall, kitchen, garden, hall_key, kitchen_apple = buildWorld()
        save_data = {'current_area': 'hall', 'inventory': [{'name': '  '}]}

        self.assertRaises(ValueError, Game.load, save_data, [hall, kitchen])

    def test_load_rejects_none_and_non_dict(self):
        self.assertRaises(ValueError, Game.load, None, [])
        self.assertRaises(ValueError, Game.load, 'not a dict', [])
