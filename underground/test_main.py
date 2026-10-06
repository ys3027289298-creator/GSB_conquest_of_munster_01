import contextlib
import copy
import io
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

# --- test environment stubs (no display / no tkinter in CI) ---
os.system = lambda *a, **k: 0
_tk = types.ModuleType("tkinter")
_mb = types.ModuleType("tkinter.messagebox")
_mb.showerror = lambda *a, **k: None
_mb.showinfo = lambda *a, **k: None
_mb.showwarning = lambda *a, **k: None
_tk.messagebox = _mb
sys.modules.setdefault("tkinter", _tk)
sys.modules.setdefault("tkinter.messagebox", _mb)

import main


class ExitLoop(Exception):
    """Raised by the fake input() when scripted responses run out."""


def make_input(responses):
    it = iter(responses)

    def fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise ExitLoop()

    return fake_input


def run_quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class GameTestCase(unittest.TestCase):
    def setUp(self):
        self._patchers = [
            mock.patch.object(main, "sleep", lambda *a, **k: None),
            mock.patch.object(main, "cls", lambda *a, **k: None),
            mock.patch("time.sleep", lambda *a, **k: None),
        ]
        for p in self._patchers:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self._monsters = copy.deepcopy(main.monsters)
        self._bosses = copy.deepcopy(main.bosses)
        self.addCleanup(self._restore)

        main.lv = 1
        main.exp = 0
        main.maxHP = 100
        main.hp = 100
        main.maxMP = 100
        main.mp = 0
        main.inventory = [main.nothing] * 8
        main.weapon = main.stick
        main.armor = main.bandage
        main.atk = 0
        main.atkFin = 0
        main.dfn = 0
        main.dfnFin = 0
        main.room = main.dogRoom
        main.gold = 0
        main.name = "Hero"
        main.gender = "m"
        main.atk_bonus = 0
        main.mp_bonus = 0
        main.appearance = ""
        main.kills = 0
        main.spared = 0
        main.pacifist_eligible = True
        main.dirtyHacker = False
        main.OKAK = False

    def _restore(self):
        main.monsters = self._monsters
        main.bosses = self._bosses
        main.room = main.dogRoom

    def run_loop(self, responses):
        with mock.patch("builtins.input", make_input(responses)):
            with self.assertRaises(ExitLoop):
                run_quiet(main.game_loop)


class StateMigrationTests(GameTestCase):
    def test_save_load_roundtrip_restores_full_character_state(self):
        main.name = "Hero"
        main.gender = "f"
        main.atk_bonus = 5
        main.mp_bonus = -20
        main.appearance = "A stocky female with red hair and blue eyes."
        main.room = main.catRoom
        main.hp = 42
        main.mp = 7
        main.lv = 3
        main.exp = 100
        main.gold = 55
        main.weapon = main.scrap
        main.armor = main.catCloak
        main.inventory = [main.bread, main.flakes] + [main.nothing] * 6
        main.kills = 2
        main.spared = 1
        main.dirtyHacker = False
        main.pacifist_eligible = True
        main.OKAK = True
        main.monsters["The Dog Room"] = 3
        main.bosses["Doge"] = False

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "save.json")
            run_quiet(main.save_game, path)

            main.gender = ""
            main.atk_bonus = 0
            main.mp_bonus = 0
            main.appearance = ""
            main.room = main.dogRoom
            main.hp = 1
            main.mp = 0
            main.lv = 1
            main.exp = 0
            main.gold = 0
            main.weapon = main.stick
            main.armor = main.bandage
            main.inventory = [main.nothing] * 8
            main.kills = 0
            main.spared = 0
            main.OKAK = False
            main.monsters = dict(self._monsters)
            main.bosses = dict(self._bosses)

            self.assertTrue(run_quiet(main.load_game, path))

        self.assertEqual(main.name, "Hero")
        self.assertEqual(main.gender, "f")
        self.assertEqual(main.atk_bonus, 5)
        self.assertEqual(main.mp_bonus, -20)
        self.assertEqual(main.appearance, "A stocky female with red hair and blue eyes.")
        self.assertIs(main.room, main.catRoom)
        self.assertEqual(main.hp, 42)
        self.assertEqual(main.mp, 7)
        self.assertEqual(main.lv, 3)
        self.assertEqual(main.exp, 100)
        self.assertEqual(main.gold, 55)
        self.assertIs(main.weapon, main.scrap)
        self.assertIs(main.armor, main.catCloak)
        self.assertEqual(main.inventory[:2], [main.bread, main.flakes])
        self.assertEqual(main.kills, 2)
        self.assertEqual(main.spared, 1)
        self.assertTrue(main.OKAK)
        self.assertEqual(main.monsters["The Dog Room"], 3)
        self.assertFalse(main.bosses["Doge"])

    def test_nextroom_moves_and_keeps_player_state(self):
        main.room = main.catRoom
        main.hp = 77
        main.mp = 13
        self.run_loop(["nextroom"])
        self.assertIs(main.room, main.ancientLib)
        self.assertEqual(main.hp, 77)
        self.assertEqual(main.mp, 13)
        self.assertIs(main.weapon, main.stick)


class MapBoundaryTests(GameTestCase):
    def test_room_chain_terminates_at_final_room(self):
        room = main.dogRoom
        seen = [room]
        for _ in range(20):
            if room.final:
                break
            self.assertIsInstance(room.nextRoom, main.Room)
            room = room.nextRoom
            seen.append(room)
        self.assertIs(seen[-1], main.finalRoom)
        self.assertTrue(main.finalRoom.final)

    def test_rooms_with_enemies_have_monster_entries(self):
        rooms = [main.dogRoom, main.pianoRoom, main.catRoom, main.ancientLib,
                 main.lab, main.spiderRoom, main.warehouse, main.chargeRoom,
                 main.finalRoom]
        for room in rooms:
            if room.enemies:
                self.assertIn(room.name, main.monsters)

    def test_unknown_room_name_falls_back_to_safe_room(self):
        self.assertIs(main.get_room_by_name("Nowhere Land"), main.dogRoom)

    def test_nextroom_without_exit_does_not_crash(self):
        main.room = main.roomOfDog
        self.run_loop(["nextroom"])
        self.assertIs(main.room, main.roomOfDog)

    def test_seek_in_room_without_enemies_does_not_crash(self):
        main.room = main.roomOfDog
        with mock.patch.object(main.rnd, "randint", return_value=10):
            self.run_loop(["seek"])

    def test_empty_action_is_ignored(self):
        self.run_loop(["", "  "])
        self.assertIs(main.room, main.dogRoom)


class FailurePathTests(GameTestCase):
    def make_enemy(self, **kwargs):
        params = dict(name="Training Dummy", hp=30, maxHP=30, atk=10,
                      exp=5, text="stands still.")
        params.update(kwargs)
        return main.Enemy(**params)

    def test_empty_battle_action_does_not_give_enemy_free_hit(self):
        enemy = self.make_enemy()
        with mock.patch("builtins.input", make_input(["", "flee"])):
            run_quiet(main.battle, enemy)
        self.assertEqual(main.hp, 100)

    def test_unknown_battle_action_does_not_give_enemy_free_hit(self):
        enemy = self.make_enemy()
        with mock.patch("builtins.input", make_input(["dance", "flee"])):
            run_quiet(main.battle, enemy)
        self.assertEqual(main.hp, 100)

    def test_gameover_restores_hp(self):
        main.hp = 0
        with mock.patch.object(main, "load_game", return_value=True), \
             mock.patch("builtins.input", make_input([""])):
            run_quiet(main.gameover)
        self.assertEqual(main.hp, main.maxHP)

    def test_trap_death_recovers_via_gameover(self):
        main.hp = 10
        with mock.patch.object(main.rnd, "randint", return_value=42), \
             mock.patch.object(main, "load_game", return_value=True):
            self.run_loop(["seek", ""])
        self.assertEqual(main.hp, main.maxHP)

    def test_wrong_puzzle_answer_keeps_room(self):
        main.room = main.lab
        self.run_loop(["nextroom", "xyz"])
        self.assertIs(main.room, main.lab)

    def test_correct_puzzle_answer_opens_path(self):
        main.room = main.lab
        self.run_loop(["nextroom", "B F Y"])
        self.assertIs(main.room, main.spiderRoom)

    def test_load_missing_save_returns_false(self):
        self.assertFalse(run_quiet(main.load_game, "definitely_missing_save.json"))

    def test_item_command_rejects_empty_input(self):
        self.run_loop(["item", ""])
        self.assertEqual(main.inventory, [main.nothing] * 8)


class ItemTests(GameTestCase):
    def test_trade_item_cannot_be_taken_twice(self):
        npc = main.NPC("Trader", ["hello"], items=[main.bread], trade=True)
        main.room = main.Room("Trade Room", None, main.dogRoom, False, [],
                              npc=[npc])
        self.run_loop(["talk", "0", "0", "talk", "0", "0"])
        self.assertEqual(main.inventory.count(main.bread), 1)
        self.assertEqual(npc.items, [])

    def test_chest_cannot_be_looted_twice(self):
        chest = main.Chest([main.bread])
        main.room = main.Room("Chest Room", None, main.dogRoom, False, [],
                              chest=chest)
        self.run_loop(["open", "open"])
        self.assertEqual(main.inventory.count(main.bread), 1)


class BattleSettlementTests(GameTestCase):
    def test_enemy_hit_keeps_hp_integral_and_reports_applied_damage(self):
        enemy = main.Enemy(name="Leopold", hp=75, maxHP=75, atk=10, exp=25,
                           text="is failing on your head!")
        out = io.StringIO()
        with mock.patch("builtins.input", make_input(["act", "scold", "flee"])), \
             contextlib.redirect_stdout(out):
            main.battle(enemy)
        # scold -> dmgMP 1.5 -> applied damage int((10 - 2) * 1.5) == 12
        self.assertIsInstance(main.hp, int)
        self.assertEqual(main.hp, 88)
        self.assertIn("You got 12 damage", out.getvalue())

    def test_kill_grants_exp_and_counts_kill(self):
        enemy = main.Enemy(name="Training Dummy", hp=5, maxHP=5, atk=1,
                           exp=7, text="stands still.")
        main.weapon = main.scrap
        with mock.patch("builtins.input", make_input(["attack"])), \
             mock.patch.object(main.rnd, "random", return_value=0.9), \
             mock.patch.object(main.rnd, "randint", return_value=100):
            run_quiet(main.battle, enemy)
        self.assertEqual(main.kills, 1)
        self.assertEqual(main.exp, 7)
        self.assertEqual(main.monsters["The Dog Room"], 7)
        self.assertGreater(main.gold, 0)

    def test_sparing_boss_marks_it_defeated(self):
        main.atkFin = 9999
        with mock.patch("builtins.input", make_input(["spare"])):
            run_quiet(main.battle, main.doge)
        self.assertEqual(main.spared, 1)
        self.assertFalse(main.bosses["Doge"])


if __name__ == "__main__":
    unittest.main()
