"""A full inventory cannot pick up items (bug #5)."""
from game.data.characters.equipment.Items import Item
from tests.helpers import QuietTestCase, make_game, make_game_main


class InventoryCapacityTest(QuietTestCase):

    def setUp(self):
        super().setUp()
        self.game = make_game(0)
        self.game_main = make_game_main(self.game)
        self.tile = self.game.x
        self.equipment = self.game.player.Eq1

    def test_full_inventory_leaves_ground_items(self):
        self.equipment.capacity = len(self.equipment.elements)
        self.game.items_map[self.tile].append(Item("Potato"))
        self.game_main.collect_items(self.tile)
        self.assertEqual(len(self.game.items_map[self.tile]), 1)
        self.assertEqual(len(self.equipment.elements), self.equipment.capacity)

    def test_pickup_stops_at_capacity(self):
        self.equipment.capacity = len(self.equipment.elements) + 1
        for name in ["Potato", "Bottle of Water", "Apple"]:
            self.game.items_map[self.tile].append(Item(name))
        self.game_main.collect_items(self.tile)
        self.assertEqual(len(self.equipment.elements), self.equipment.capacity)
        self.assertEqual(len(self.game.items_map[self.tile]), 2)

    def test_pickup_when_room_available_still_works(self):
        for name in ["Potato", "Bottle of Water"]:
            self.game.items_map[self.tile].append(Item(name))
        self.game_main.collect_items(self.tile)
        self.assertEqual(self.game.items_map[self.tile], [])
        names = self.equipment.items_names()
        self.assertIn("Potato", names)
        self.assertIn("Bottle of Water", names)
