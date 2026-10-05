"""World state migration: objects and variables mutate, save, and restore."""
import unittest

from helpers import make_and_run, make_game, run_game

SWORD = ('<object name="sword">'
         '<alias>Iron Sword</alias>'
         '<damage>5</damage>'
         '</object>')


class WorldStateTests(unittest.TestCase):
    def test_script_mutation_of_object_persists(self):
        game, out, err = make_and_run(start="sword.damage = 7", extra=SWORD)
        self.assertEqual(err, "")
        self.assertEqual(game.objects["sword"].damage, 7)

    def test_script_variables_persist_across_scripts(self):
        function = ('<function name="Spend">'
                    'gold = gold - 1\n'
                    'return (gold)'
                    '</function>')
        game, out, err = make_and_run(start="gold = 10\nmsg(Spend())", extra=function)
        self.assertEqual(err, "")
        self.assertIn("9", out)
        self.assertEqual(game.script_engine.namespace["gold"], 9)

    def test_save_and_load_restores_object_and_variables(self):
        game, out, err = make_and_run(start="sword.damage = 7\nfound = true", extra=SWORD)
        self.assertEqual(err, "")
        state = game.save_state()
        # Mutate the live world after saving.
        game.objects["sword"].damage = 99
        game.script_engine.namespace["found"] = False
        game.load_state(state)
        self.assertEqual(game.objects["sword"].damage, 7)
        self.assertEqual(game.script_engine.namespace["found"], True)

    def test_save_state_is_a_deep_snapshot(self):
        game, out, err = make_and_run(start="sword.damage = 7", extra=SWORD)
        state = game.save_state()
        game.objects["sword"].damage = 99
        self.assertEqual(state["objects"]["sword"]["damage"], 7)

    def test_events_are_part_of_saved_state(self):
        function = ('<function name="Look">firsttime {\n'
                    'msg("first")\n'
                    '}\n'
                    'otherwise {\n'
                    'msg("later")\n'
                    '}</function>')
        game, out, err = make_and_run(start="Look()", extra=function)
        self.assertEqual(len(game.script_engine.events_fired), 1)
        state = game.save_state()
        game.script_engine.events_fired.clear()
        game.load_state(state)
        self.assertEqual(len(game.script_engine.events_fired), 1)

    def test_load_state_with_unknown_object_fails_cleanly(self):
        game, out, err = make_and_run(start="sword.damage = 7", extra=SWORD)
        state = game.save_state()
        state["objects"]["ghost"] = {"name": "ghost"}
        with self.assertRaises(KeyError):
            game.load_state(state)

    def test_games_do_not_leak_state_into_each_other(self):
        game1, out1, err1 = make_and_run(start="score = 42")
        self.assertEqual(err1, "")
        # A fresh game must not see the first game's variables.
        game2, out2, err2 = make_and_run(start="msg(score)")
        self.assertIn("NameError", err2)
        self.assertNotIn("42", out2)


if __name__ == "__main__":
    unittest.main()
