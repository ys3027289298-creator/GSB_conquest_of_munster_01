import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'game'))

from Creatures import Monster


class TestMonster(unittest.TestCase):

    def test_valid_monster(self):
        monster = Monster(name='kevin', level=20, height=45, attack=20)
        self.assertEqual(monster.describe(), 'kevin, 20, 45, 20')
        self.assertEqual(monster.hp, 200)
        self.assertTrue(monster.is_alive())

    def test_out_of_bounds_stats_rejected(self):
        with self.assertRaises(ValueError):
            Monster(name='a', level=0)
        with self.assertRaises(ValueError):
            Monster(name='a', level=Monster.MAX_LEVEL + 1)
        with self.assertRaises(ValueError):
            Monster(name='a', height=-1)
        with self.assertRaises(ValueError):
            Monster(name='a', attack=Monster.MAX_ATTACK + 1)
        with self.assertRaises(ValueError):
            Monster(name='a', hp=0)
        with self.assertRaises(ValueError):
            Monster(name='a', hp=Monster.MAX_HP + 1)

    def test_bad_types_rejected(self):
        with self.assertRaises(TypeError):
            Monster(name='a', level='high')
        with self.assertRaises(TypeError):
            Monster(name='a', attack=None)
        with self.assertRaises(ValueError):
            Monster(name='')

    def test_missing_attribute_raises_keyerror(self):
        monster = Monster(name='kevin')
        with self.assertRaises(KeyError):
            monster['nonexistent']
        self.assertEqual(monster['name'], 'kevin')

    def test_take_damage_and_death(self):
        monster = Monster(name='kevin', level=1)
        monster.take_damage(5)
        self.assertEqual(monster.hp, 5)
        monster.take_damage(100)
        self.assertEqual(monster.hp, 0)
        self.assertFalse(monster.is_alive())
        with self.assertRaises(ValueError):
            monster.take_damage(-1)


if __name__ == '__main__':
    unittest.main()
