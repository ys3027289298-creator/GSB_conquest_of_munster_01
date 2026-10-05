"""
Regression tests for The Vengeful Wyrm.

Covers the six fixed defects:
1. hit points could leave the valid range (negative after a lethal hit)
2. dice results were not reproducible (unseeded global RNG only)
3. the health bar rendered negative values / wrong segment counts
4. an invalid "play again" answer restarted the whole mission
5. the riddle path looped forever when the input stream ended (EOF)
6. the story advanced (game reported a win) even after a lost fight

Dice and game-state tests use fixed seeds (random.Random) so they are
fully deterministic. Narrative text files are replaced by placeholders
in a temporary directory; the real story content is not touched.
"""

import io
import os
import random
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- stub optional third-party dependencies not needed for logic tests ---
_simple_colors = types.ModuleType("simple_colors")
def _color(text, styles=None):
    return str(text)
for _name in ("red", "blue", "green", "yellow", "magenta", "cyan"):
    setattr(_simple_colors, _name, _color)
sys.modules.setdefault("simple_colors", _simple_colors)

_charimage = types.ModuleType("tvw_charimage")
_charimage.dwarf_img = _charimage.elf_img = _charimage.wizzard_img = ""
_charimage.wyrm_img = ""
_charimage.display_image = lambda *args, **kwargs: None
_charimage.display_wyrm = lambda *args, **kwargs: None
sys.modules.setdefault("tvw_charimage", _charimage)

import tvw_dices
import tvw_fight
import tvw_healthbar
import tvw_path
import tvw_game

STORY_FILES = ("intro", "dwarf", "elf", "human", "mission",
               "mission_decline", "mission_accept", "forest")

_story_dir = None
_prev_cwd = None
_sleep_patcher = None


def setUpModule():
    global _story_dir, _prev_cwd, _sleep_patcher
    _story_dir = tempfile.TemporaryDirectory()
    for name in STORY_FILES:
        with open(os.path.join(_story_dir.name, name + ".txt"), "w",
                  encoding="utf-8") as f:
            f.write(f"placeholder {name} text")
    _prev_cwd = os.getcwd()
    os.chdir(_story_dir.name)
    _sleep_patcher = mock.patch("time.sleep")
    _sleep_patcher.start()


def tearDownModule():
    global _story_dir
    _sleep_patcher.stop()
    os.chdir(_prev_cwd)
    _story_dir.cleanup()
    _story_dir = None


def run_game(inputs, rng=None):
    """Run one playthrough with scripted input, returning (result, output)."""
    out = io.StringIO()
    with mock.patch("builtins.input", side_effect=list(inputs)), \
         mock.patch("sys.stdout", out):
        result = tvw_game.the_vengeful_wyrm(rng=rng)
    return result, out.getvalue()


class TestDice(unittest.TestCase):
    def test_enemy_d20_fixed_seed(self):
        rng = random.Random(42)
        expected = [random.Random(42).randint(1, 20) for _ in range(10)]
        # recompute expected from an identical generator
        gen = random.Random(42)
        expected = [gen.randint(1, 20) for _ in range(10)]
        with mock.patch("sys.stdout", io.StringIO()):
            rolls = [tvw_dices.enemy_D20(rng=rng) for _ in range(10)]
        self.assertEqual(rolls, expected)
        self.assertTrue(all(1 <= r <= 20 for r in rolls))

    def test_enemy_d6_fixed_seed_and_bounds(self):
        wyrm = {"damage": 2}
        rng = random.Random(7)
        gen = random.Random(7)
        expected = [gen.randint(1, 6) for _ in range(10)]
        with mock.patch("sys.stdout", io.StringIO()):
            rolls = [tvw_dices.enemy_D6(wyrm, rng=rng) for _ in range(10)]
        self.assertEqual(rolls, expected)
        self.assertTrue(all(1 <= r <= 6 for r in rolls))

    def test_user_d20_fixed_seed(self):
        rng = random.Random(3)
        gen = random.Random(3)
        expected = [gen.randint(1, 20) for _ in range(5)]
        with mock.patch("builtins.input", return_value="r"), \
             mock.patch("sys.stdout", io.StringIO()):
            rolls = [tvw_dices.user_D20(rng=rng) for _ in range(5)]
        self.assertEqual(rolls, expected)

    def test_user_d6_adds_damage_modifier(self):
        user = {"damage": 3}
        rng = random.Random(11)
        gen = random.Random(11)
        expected = [gen.randint(1, 6) + 3 for _ in range(5)]
        with mock.patch("builtins.input", return_value="r"), \
             mock.patch("sys.stdout", io.StringIO()):
            totals = [tvw_dices.user_D6(user, rng=rng) for _ in range(5)]
        self.assertEqual(totals, expected)

    def test_rolls_isolated_from_global_rng(self):
        # the original bug: results depended on global RNG consumers
        rng = random.Random(99)
        gen = random.Random(99)
        expected = [gen.randint(1, 20) for _ in range(5)]
        random.seed(1234)  # perturb the global generator
        random.random()
        with mock.patch("sys.stdout", io.StringIO()):
            rolls = [tvw_dices.enemy_D20(rng=rng) for _ in range(5)]
        self.assertEqual(rolls, expected)


class TestStateBounds(unittest.TestCase):
    def test_user_hit_points_never_negative(self):
        user = {"hit points": 3, "armor_class": 2}
        enemy = {"attack bonus": 5, "damage": 2, "armor_class": 99}
        with mock.patch("sys.stdout", io.StringIO()):
            tvw_fight.enemy_attack(lambda rng=None: 20, lambda e, rng=None: 6,
                                   user, enemy)
        self.assertEqual(user["hit points"], 0)

    def test_enemy_hit_points_never_negative(self):
        user = {"attack bonus": 3, "damage": 2}
        enemy = {"hit points": 4, "armor_class": 10}
        with mock.patch("sys.stdout", io.StringIO()):
            tvw_fight.user_attack(lambda rng=None: 20, lambda u, rng=None: 6,
                                  user, enemy)
        self.assertEqual(enemy["hit points"], 0)


class TestHealthBar(unittest.TestCase):
    def _draw(self, bar):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            bar.draw()
        return out.getvalue()

    def test_negative_hp_clamped(self):
        entity = {"hit points": 15}
        bar = tvw_healthbar.HealthBar(entity)
        entity["hit points"] = -3
        bar.update()
        drawn = self._draw(bar)
        self.assertIn("0/15", drawn)
        self.assertNotIn("-3", drawn)
        self.assertEqual(drawn.count("█") + drawn.count("_"), 20)

    def test_overheal_bar_not_longer_than_length(self):
        entity = {"hit points": 15}
        bar = tvw_healthbar.HealthBar(entity)
        entity["hit points"] = 20
        bar.update()
        drawn = self._draw(bar)
        self.assertEqual(drawn.count("█") + drawn.count("_"), 20)

    def test_enemy_bar_clamped(self):
        entity = {"hit points": 20}
        bar = tvw_healthbar.HealthBar_Enemy(entity)
        entity["hit points"] = -5
        bar.update()
        drawn = self._draw(bar)
        self.assertEqual(drawn.count("█") + drawn.count("_"), 20)


class TestMission(unittest.TestCase):
    def test_declining_mission_does_not_advance_story(self):
        result, output = run_game(["1", "Hero", "no", "yes"])
        self.assertFalse(result)
        self.assertNotIn("Chapter Three", output)
        self.assertNotIn("Right Path", output)

    def test_mission_completed_exactly_once(self):
        inputs = ["1", "Hero", "yes", "1", "future"] + ["r"] * 500
        result, output = run_game(inputs, rng=random.Random(4))
        self.assertTrue(result)
        self.assertEqual(output.count("Chapter One"), 1)
        self.assertEqual(output.count("placeholder mission_accept text"), 1)

    def test_invalid_play_again_answer_does_not_restart_mission(self):
        with mock.patch.object(tvw_game, "the_vengeful_wyrm",
                               return_value=True) as play, \
             mock.patch("builtins.input", side_effect=["maybe", "nope", "no"]), \
             mock.patch("sys.stdout", io.StringIO()):
            tvw_game.main()
        self.assertEqual(play.call_count, 1)

    def test_ask_play_again_reprompts_until_valid(self):
        with mock.patch("builtins.input", side_effect=["maybe", "yes"]), \
             mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(tvw_game.ask_play_again(), "yes")


class TestPath(unittest.TestCase):
    def test_riddle_returns_false_on_eof_instead_of_looping(self):
        result = {}
        def run():
            with mock.patch("builtins.input", side_effect=EOFError), \
                 mock.patch("sys.stdout", io.StringIO()):
                result["value"] = tvw_path.riddle("Hero")
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        thread.join(2)
        self.assertFalse(thread.is_alive(), "riddle() loops forever on EOF")
        self.assertIs(result["value"], False)

    def test_riddle_empty_answer_reprompts(self):
        with mock.patch("builtins.input", side_effect=["", "future"]), \
             mock.patch("sys.stdout", io.StringIO()):
            self.assertTrue(tvw_path.riddle("Hero"))

    def test_failed_riddle_does_not_reach_wyrm(self):
        result, output = run_game(["1", "Hero", "yes", "1", "wrong answer"])
        self.assertFalse(result)
        self.assertNotIn("Chapter Three", output)
        self.assertNotIn("placeholder forest text", output)

    def test_failed_river_does_not_reach_wyrm(self):
        # seed 1: D20 skill check + athletics stays below the DC
        inputs = ["1", "Hero", "yes", "2", "r"]
        result, output = run_game(inputs, rng=random.Random(1))
        self.assertFalse(result)
        self.assertNotIn("Chapter Three", output)
        self.assertNotIn("placeholder forest text", output)


class TestFight(unittest.TestCase):
    def _stats(self):
        user = dict(tvw_game.original_characters["first"])
        enemy = dict(tvw_game.original_wyrm)
        return user, enemy

    def test_fight_returns_false_when_user_dies(self):
        user, enemy = self._stats()
        with mock.patch("builtins.input", return_value="r"), \
             mock.patch("sys.stdout", io.StringIO()):
            result = tvw_fight.fight(user, enemy, "Hero", rng=random.Random(1))
        self.assertIs(result, False)
        self.assertEqual(user["hit points"], 0)

    def test_fight_returns_true_when_wyrm_dies(self):
        user, enemy = self._stats()
        with mock.patch("builtins.input", return_value="r"), \
             mock.patch("sys.stdout", io.StringIO()):
            result = tvw_fight.fight(user, enemy, "Hero", rng=random.Random(4))
        self.assertIs(result, True)
        self.assertEqual(enemy["hit points"], 0)

    def test_lost_fight_does_not_advance_story(self):
        inputs = ["1", "Hero", "yes", "1", "future"] + ["r"] * 500
        result, output = run_game(inputs, rng=random.Random(1))
        self.assertFalse(result)
        self.assertNotIn("Happy end", output)

    def test_won_fight_reaches_happy_end(self):
        inputs = ["1", "Hero", "yes", "1", "future"] + ["r"] * 500
        result, output = run_game(inputs, rng=random.Random(4))
        self.assertTrue(result)
        self.assertIn("Happy end", output)


if __name__ == "__main__":
    unittest.main()
