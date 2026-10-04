import unittest
from unittest.mock import patch

from weapons.bow import Bow
from weapons.shield import Shield
from weapons.spear import Spear
from weapons.staff import Staff
from enemies.dragon import Dragon
from enemies.dummy import Training_Dummy
from tests.helpers import no_sleep


WEAPONS = {
    "Bow": (Bow, "Power Shot"),
    "Shield": (Shield, "Shield Bash"),
    "Staff": (Staff, "Fireball"),
    "Spear": (Spear, "Icicle"),
}


class WeaponTypeTests(unittest.TestCase):
    def setUp(self):
        no_sleep().start()
        self.addCleanup(stop_all)

    def test_every_weapon_has_five_well_formed_abilities(self):
        for weapon_name, (cls, signature) in WEAPONS.items():
            with self.subTest(weapon=weapon_name):
                player = cls("Hero")
                self.assertEqual(list(player.abilities)[0], "Attack")
                self.assertEqual(len(player.abilities), 5)
                self.assertIn(signature, player.abilities)
                for ability in player.abilities.values():
                    self.assertIn("mana cost", ability)
                    self.assertIn("damage multiplier", ability)
                    self.assertIn("element", ability)
                    self.assertGreater(ability["mana cost"], -1)
                    self.assertGreater(ability["damage multiplier"], 0)

    def test_weapon_types_map_to_their_classes(self):
        self.assertIsInstance(Bow("H"), Bow)
        self.assertIsInstance(Shield("H"), Shield)
        self.assertIsInstance(Staff("H"), Staff)
        self.assertIsInstance(Spear("H"), Spear)


def stop_all():
    patch.stopall()


class DamageBoundaryTests(unittest.TestCase):
    def setUp(self):
        no_sleep().start()

    def tearDown(self):
        patch.stopall()

    def test_damage_equal_to_health_kills_at_zero_boundary(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        dragon.health = 5
        player.use_ability("Attack", dragon)
        self.assertEqual(dragon.health, 0)
        self.assertFalse(dragon.is_alive)

    def test_overkill_damage_does_not_go_negative(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        dragon.health = 3
        player.use_ability("Attack", dragon)
        self.assertEqual(dragon.health, 0)
        self.assertFalse(dragon.is_alive)

    def test_nonlethal_hit_keeps_target_alive(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        player.use_ability("Attack", dragon)
        self.assertEqual(dragon.health, 95)
        self.assertTrue(dragon.is_alive)

    def test_enemy_overkill_reports_actual_taken_damage(self):
        dragon = Dragon("Oolong")
        player = Bow("Hero")
        player.health = 3
        dragon.use_ability("Claw", player)
        self.assertEqual(player.health, 0)
        self.assertFalse(player.is_alive)

    def test_mana_exactly_at_cost_boundary_still_casts(self):
        player = Bow("Hero")
        player.mana = 10
        dragon = Dragon("Oolong")
        player.use_ability("Power Shot", dragon)
        self.assertEqual(player.mana, 0)
        self.assertEqual(dragon.health, 90)

    def test_insufficient_mana_refunds_mana_and_deals_no_damage(self):
        player = Bow("Hero")
        player.mana = 9
        dragon = Dragon("Oolong")
        player.use_ability("Power Shot", dragon)
        self.assertEqual(player.mana, 9)
        self.assertEqual(dragon.health, 100)


class ElementAndPotionTests(unittest.TestCase):
    def setUp(self):
        no_sleep().start()

    def tearDown(self):
        patch.stopall()

    def test_weakness_and_resistance_adjust_damage(self):
        ice_dummy = Training_Dummy("Ice Dummy")
        ice_dummy.element = "ice"
        dragon = Dragon("Oolong")
        player = Staff("Hero")
        player.use_ability("Fireball", ice_dummy)
        self.assertEqual(ice_dummy.health, 9984)
        player.use_ability("Fireball", dragon)
        self.assertEqual(dragon.health, 95)

    def test_strong_resistance_reduces_damage(self):
        fire_dummy = Training_Dummy("Fire Dummy")
        fire_dummy.element = "fire"
        player = Staff("Hero")
        player.use_ability("Fireball", fire_dummy)
        self.assertEqual(fire_dummy.health, 9994)
        self.assertTrue(fire_dummy.is_alive)

    def test_potion_is_consumed_and_capped_at_full_stats(self):
        player = Bow("Hero")
        player.add_item("potion")
        self.assertEqual(player.potions, 1)
        player.health = 80
        player.mana = 80
        player.use_potion()
        self.assertEqual(player.potions, 0)
        self.assertEqual(player.health, 100)
        self.assertEqual(player.mana, 100)

    def test_potion_revives_fallen_player(self):
        player = Bow("Hero")
        player.add_item("potion")
        player.health = 0
        player.is_alive = False
        player.use_potion()
        self.assertTrue(player.is_alive)
        self.assertEqual(player.health, 50)

    def test_dead_actor_cannot_use_abilities(self):
        player = Bow("Hero")
        dragon = Dragon("Oolong")
        player.is_alive = False
        player.use_ability("Attack", dragon)
        self.assertEqual(dragon.health, 100)


if __name__ == "__main__":
    unittest.main()
