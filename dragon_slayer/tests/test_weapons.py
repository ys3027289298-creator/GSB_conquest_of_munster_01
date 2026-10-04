import builtins
import contextlib
import io
import unittest
from unittest import mock

from weapons.bow import Bow
from weapons.shield import Shield
from weapons.staff import Staff
from weapons.spear import Spear
from enemies.dragon import Dragon
from enemies.enemy import Enemy
from story.intro import intro


def no_sleep(*args, **kwargs):
    return None


class WeaponTypesTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("time.sleep", no_sleep)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_all_weapon_types_have_five_abilities_with_attack(self):
        for weapon_class in (Bow, Shield, Staff, Spear):
            with self.subTest(weapon=weapon_class.__name__):
                player = weapon_class("Hero")
                self.assertEqual(len(player.abilities), 5)
                self.assertIn("Attack", player.abilities)
                self.assertEqual(player.abilities["Attack"]["mana cost"], 0)
                for ability in player.abilities.values():
                    self.assertIn("mana cost", ability)
                    self.assertIn("damage multiplier", ability)
                    self.assertIn("element", ability)

    def test_intro_creates_each_weapon_type(self):
        expected = {"1": Bow, "2": Shield, "3": Staff, "4": Spear}
        for choice, weapon_class in expected.items():
            with self.subTest(choice=choice):
                inputs = iter(["Hero", choice])
                with mock.patch.object(builtins, "input", lambda prompt="": next(inputs)):
                    with contextlib.redirect_stdout(io.StringIO()):
                        player = intro()
                self.assertIsInstance(player, weapon_class)
                self.assertEqual(player.name, "Hero")


class DamageBoundaryTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("time.sleep", no_sleep)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def test_exact_mana_cost_can_be_cast(self):
        player = Bow("Hero")
        player.mana = 15
        dragon = Dragon("Oolong")
        player.use_ability("Ice Arrow", dragon)
        self.assertEqual(player.mana, 0)
        self.assertEqual(dragon.health, 100 - 22)

    def test_insufficient_mana_is_not_deducted(self):
        player = Bow("Hero")
        player.mana = 10
        dragon = Dragon("Oolong")
        player.use_ability("Ice Arrow", dragon)
        self.assertEqual(player.mana, 10)
        self.assertEqual(dragon.health, 100)
        self.assertIn("Not enough mana.", self.output.getvalue())

    def test_weak_element_adds_bonus_damage(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        player.use_ability("Ice Arrow", dragon)
        self.assertEqual(dragon.health, 100 - 22)

    def test_resisted_element_reduces_damage(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        player.use_ability("Fire Arrow", dragon)
        self.assertEqual(dragon.health, 100 - 8)

    def test_kill_at_exact_health_boundary(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        dragon.health = 22
        player.use_ability("Ice Arrow", dragon)
        self.assertEqual(dragon.health, 0)
        self.assertFalse(dragon.is_alive)

    def test_overkill_never_leaves_negative_health(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        dragon.health = 5
        player.use_ability("Ice Arrow", dragon)
        self.assertEqual(dragon.health, 0)
        self.assertFalse(dragon.is_alive)

    def test_non_lethal_hit_keeps_target_alive(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        player.use_ability("Attack", dragon)
        self.assertEqual(dragon.health, 95)
        self.assertTrue(dragon.is_alive)


class PotionTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("time.sleep", no_sleep)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def test_potion_is_consumed_and_revives(self):
        player = Bow("Hero")
        player.health = 0
        player.is_alive = False
        player.mana = 0
        player.potions = 1
        player.use_potion()
        self.assertEqual(player.potions, 0)
        self.assertEqual(player.health, 50)
        self.assertEqual(player.mana, 50)
        self.assertTrue(player.is_alive)

    def test_second_potion_use_finds_empty_inventory(self):
        player = Bow("Hero")
        player.health = 0
        player.is_alive = False
        player.potions = 1
        player.use_potion()
        player.health = 0
        player.is_alive = False
        player.use_potion()
        self.assertEqual(player.health, 0)
        self.assertFalse(player.is_alive)
        self.assertIn("No potions found.", self.output.getvalue())


class EnemyAttackTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("time.sleep", no_sleep)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def test_lethal_hit_marks_player_dead(self):
        dragon = Dragon("Oolong")
        player = Bow("Hero")
        player.health = 50
        dragon.use_ability("Dragonbreath", player)
        self.assertEqual(player.health, 0)
        self.assertFalse(player.is_alive)

    def test_non_lethal_hit_keeps_player_alive(self):
        dragon = Dragon("Oolong")
        player = Bow("Hero")
        dragon.use_ability("Claw", player)
        self.assertEqual(player.health, 90)
        self.assertTrue(player.is_alive)


if __name__ == "__main__":
    unittest.main()
