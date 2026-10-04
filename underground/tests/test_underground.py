import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from ug_loader import StopGame, load_module, make_input


class UndergroundTestCase(unittest.TestCase):
    def setUp(self):
        self.ug = load_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.save_path = os.path.join(self._tmp.name, "save.json")

    def run_loop(self, script):
        """Run game_loop with scripted inputs; return captured stdout."""
        out = io.StringIO()
        with mock.patch("builtins.input", make_input(script)):
            with redirect_stdout(out):
                with self.assertRaises(StopGame):
                    self.ug.game_loop()
        return out.getvalue()

    def run_loop_in_tmp(self, script):
        old_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        try:
            return self.run_loop(script)
        finally:
            os.chdir(old_cwd)

    def run_battle(self, enemy, script):
        """Run battle with scripted inputs; return (result, stdout)."""
        out = io.StringIO()
        with mock.patch("builtins.input", make_input(script)):
            with redirect_stdout(out):
                try:
                    result = self.ug.battle(enemy)
                except StopGame:
                    result = "STOPPED"
        return result, out.getvalue()

    def save(self):
        with redirect_stdout(io.StringIO()):
            self.ug.save_game(self.save_path)

    def load(self):
        with redirect_stdout(io.StringIO()):
            return self.ug.load_game(self.save_path)


class TestStateMigration(UndergroundTestCase):
    def test_load_restores_character_build(self):
        ug = self.ug
        ug.name = "Hero"
        ug.gender = "f"
        ug.atk_bonus = 5
        ug.mp_bonus = 30
        ug.appearance = "A stocky female with red hair."
        ug.OKAK = True
        self.save()

        ug.gender = "m"
        ug.atk_bonus = 0
        ug.mp_bonus = 0
        ug.appearance = ""
        ug.OKAK = False
        self.assertTrue(self.load())

        self.assertEqual(ug.gender, "f")
        self.assertEqual(ug.atk_bonus, 5)
        self.assertEqual(ug.mp_bonus, 30)
        self.assertEqual(ug.appearance, "A stocky female with red hair.")
        self.assertTrue(ug.OKAK)

    def test_load_restores_boss_state(self):
        ug = self.ug
        ug.bosses["Doge"] = False
        ug.dogRoom.boss = None
        self.save()

        ug.dogRoom.boss = ug.doge
        ug.bosses["Doge"] = True
        self.assertTrue(self.load())

        self.assertIsNone(ug.dogRoom.boss)

    def test_load_restores_chest_state_across_restart(self):
        # A brand-new module simulates restarting the game process.
        ug = self.ug
        ug.room = ug.dogRoom
        self.run_loop_in_tmp(["open", "save"])

        reloaded = load_module()
        old_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        try:
            with redirect_stdout(io.StringIO()):
                self.assertTrue(reloaded.load_game("save.json"))
        finally:
            os.chdir(old_cwd)

        self.assertTrue(reloaded.dogRoom.chest.opened)

    def test_save_load_roundtrip_progress(self):
        ug = self.ug
        ug.kills = 3
        ug.spared = 2
        ug.gold = 100
        ug.hp = 42
        ug.exp = 80
        ug.monsters["The Dog Room"] = 5
        ug.inventory[0] = ug.bread
        ug.room = ug.pianoRoom
        self.save()

        ug.kills = 0
        ug.spared = 0
        ug.gold = 0
        ug.hp = 1
        ug.exp = 0
        ug.monsters["The Dog Room"] = 8
        ug.inventory[0] = ug.nothing
        ug.room = ug.dogRoom
        self.assertTrue(self.load())

        self.assertEqual(ug.kills, 3)
        self.assertEqual(ug.spared, 2)
        self.assertEqual(ug.gold, 100)
        self.assertEqual(ug.hp, 42)
        self.assertEqual(ug.exp, 80)
        self.assertEqual(ug.monsters["The Dog Room"], 5)
        self.assertIs(ug.inventory[0], ug.bread)
        self.assertIs(ug.room, ug.pianoRoom)

    def test_chest_not_lootable_twice_across_save_load(self):
        self.ug.room = self.ug.dogRoom
        self.run_loop_in_tmp(["open", "save"])

        reloaded = load_module()
        out = io.StringIO()
        old_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        try:
            with mock.patch("builtins.input", make_input(["load", "open"])):
                with redirect_stdout(out):
                    self.assertRaises(StopGame, reloaded.game_loop)
        finally:
            os.chdir(old_cwd)
        output = out.getvalue()
        self.assertEqual(output.count("added to inventory"), 0)
        self.assertIn("The chest is already empty.", output)


class TestMapBoundaries(UndergroundTestCase):
    def test_nextroom_beyond_map_edge_does_not_crash(self):
        self.ug.room = self.ug.roomOfDog  # nextRoom == ""
        out = self.run_loop(["nextroom"])
        self.assertIn("no way forward", out)
        self.assertIs(self.ug.room, self.ug.roomOfDog)

    def test_nextroom_normal_transition(self):
        self.ug.dogRoom.boss = None
        self.ug.room = self.ug.dogRoom
        self.run_loop(["nextroom"])
        self.assertIs(self.ug.room, self.ug.pianoRoom)

    def test_puzzle_wrong_answer_blocks_room_change(self):
        self.ug.room = self.ug.lab
        out = self.run_loop(["nextroom", "WRONG"])
        self.assertIn("Wrong answer!", out)
        self.assertIs(self.ug.room, self.ug.lab)

    def test_puzzle_correct_answer_opens_path(self):
        self.ug.room = self.ug.lab
        self.run_loop(["nextroom", "B F Y"])
        self.assertIs(self.ug.room, self.ug.spiderRoom)


class TestBattleSettlement(UndergroundTestCase):
    def test_reported_damage_matches_hp_loss(self):
        ug = self.ug
        # Leopold "scold" sets dmgMP = 1.5; atk 6 vs dfnFin 2
        # real damage: int((6 - 2) * 1.5) == 6
        result, out = self.run_battle(ug.leo, ["act", "scold"])
        self.assertEqual(ug.hp, ug.maxHP - 6)
        self.assertIn("You got 6 damage", out)

    def test_kill_grants_exp_gold_and_kill_count(self):
        ug = self.ug
        ug.weapon = ug.debugWP
        with mock.patch.object(ug.rnd, "random", lambda: 0.99), \
             mock.patch.object(ug.rnd, "randint", lambda a, b: b):
            result, out = self.run_battle(ug.smolDoge, ["attack"])
        self.assertIn("YOU WON!", out)
        self.assertEqual(ug.kills, 1)
        self.assertEqual(ug.exp, ug.smolDoge.exp)
        self.assertEqual(ug.monsters["The Dog Room"], 7)
        self.assertGreater(ug.gold, 0)
        self.assertFalse(ug.pacifist_eligible)

    def test_battle_death_returns_false_and_stops(self):
        ug = self.ug
        ug.hp = 1
        calls = []
        with mock.patch.object(ug, "gameover", lambda: calls.append(1)):
            result, _ = self.run_battle(ug.dog, ["defend"])
        self.assertFalse(result)
        self.assertEqual(len(calls), 1)


class TestEmptyAndInvalidInput(UndergroundTestCase):
    def test_battle_empty_input_gives_enemy_no_turn(self):
        ug = self.ug
        _, out = self.run_battle(ug.smolDoge, [""])
        self.assertIn("Invalid input!", out)
        self.assertEqual(ug.hp, ug.maxHP)

    def test_game_loop_empty_input_reports_invalid(self):
        out = self.run_loop([""])
        self.assertIn("Invalid input!", out)

    def test_item_negative_slot_rejected(self):
        ug = self.ug
        ug.inventory[7] = ug.bread
        ug.hp = 50
        out = self.run_loop(["item", "-1"])
        self.assertIn("Invalid input!", out)
        self.assertIs(ug.inventory[7], ug.bread)
        self.assertEqual(ug.hp, 50)

    def test_seek_loot_negative_slot_rejected(self):
        ug = self.ug
        ug.inventory[7] = ug.bread
        with mock.patch.object(ug.rnd, "randint", lambda a, b: 30):
            out = self.run_loop(["seek", "-1"])
        self.assertIn("Invalid input!", out)
        self.assertIs(ug.inventory[7], ug.bread)


class TestDeathStopsTurn(UndergroundTestCase):
    def test_trap_death_does_not_continue_turn(self):
        ug = self.ug
        ug.hp = 10
        calls = []

        def fake_gameover():
            calls.append(1)
            ug.hp = ug.maxHP  # simulate successful reload

        with mock.patch.object(ug.rnd, "randint", lambda a, b: 45), \
             mock.patch.object(ug, "gameover", fake_gameover):
            out = self.run_loop(["seek"])
        self.assertEqual(len(calls), 1)
        self.assertNotIn("You got 20 damage", out)


if __name__ == "__main__":
    unittest.main()
