import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'game'))

import Load


def make_controls():
    import main
    with contextlib.redirect_stdout(io.StringIO()):
        return main.Controls()


class TestSaveLoad(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, 'save.json')

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_restore_state(self):
        controls = make_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_e('')
        controls.player.name = 'hero'
        controls.player.take_damage(30)
        controls.player.hold('wood', 'right')
        controls.inventory.add_item('wood', 4)
        controls.inventory.add_item('stone', 2)

        Load.save_game(controls, self.path)
        self.assertTrue(os.path.exists(self.path))

        fresh = make_controls()
        Load.load_game(fresh, self.path)

        self.assertEqual(fresh.loc.id, 'town')
        self.assertEqual(fresh.position, fresh.loc.name)
        self.assertEqual(fresh.player.name, 'hero')
        self.assertEqual(fresh.player.hp, 70)
        self.assertEqual(fresh.player.right_hand, 'wood')
        self.assertEqual(fresh.inventory.slots['wood'], 4)
        self.assertEqual(fresh.inventory.slots['stone'], 2)

    def test_save_file_is_valid_json(self):
        controls = make_controls()
        Load.save_game(controls, self.path)
        with open(self.path) as f:
            state = json.load(f)
        self.assertEqual(state['room'], 'intro')
        self.assertIn('inventory', state)
        self.assertIn('player', state)

    def test_load_missing_file_raises(self):
        controls = make_controls()
        with self.assertRaises(OSError):
            Load.load_game(controls, self.path)

    def test_load_corrupt_file_raises(self):
        with open(self.path, 'w') as f:
            f.write('not json{')
        controls = make_controls()
        with self.assertRaises(ValueError):
            Load.load_game(controls, self.path)

    def test_dead_state_survives_round_trip(self):
        controls = make_controls()
        controls.player.take_damage(controls.player.hp)
        Load.save_game(controls, self.path)
        fresh = make_controls()
        Load.load_game(fresh, self.path)
        self.assertFalse(fresh.player.is_alive())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            fresh.do_e('')
        self.assertEqual(fresh.loc.id, 'intro')

    def test_do_save_and_do_load_commands(self):
        controls = make_controls()
        controls.inventory.add_item('dirt', 3)
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_save(self.path)
        fresh = make_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            fresh.do_load(self.path)
        self.assertEqual(fresh.inventory.slots['dirt'], 3)


if __name__ == '__main__':
    unittest.main()
