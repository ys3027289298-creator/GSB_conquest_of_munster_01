import unittest

import tests  # noqa: F401  sets up sys.path
from Creatures import Monster
from main import Events


class MonsterTest(unittest.TestCase):

    def setUp(self):
        self.monster = Monster(name='kevin', level=20, height=45, attack=20)

    def test_known_attributes(self):
        self.assertEqual(self.monster['name'], 'kevin')
        self.assertEqual(self.monster['level'], 20)
        self.assertEqual(self.monster['attack'], 20)

    def test_missing_attribute_raises(self):
        with self.assertRaises(KeyError):
            self.monster['health']

    def test_format_map_unknown_field_raises(self):
        with self.assertRaises(KeyError):
            '{name}, {missing}'.format_map(self.monster)


class SpawnEventTest(unittest.TestCase):

    def test_spawn_returns_bool(self):
        events = Events()
        for _ in range(20):
            result = events.spawAtPos()
            self.assertIn(result, (True, False))


if __name__ == '__main__':
    unittest.main()
