import contextlib
import io
import json
import os
import tempfile
import unittest

import tests  # noqa: F401  sets up sys.path
import Load
from main import Controls


def quiet_controls():
    with contextlib.redirect_stdout(io.StringIO()):
        return Controls()


class SaveLoadTest(unittest.TestCase):

    def setUp(self):
        self.controls = quiet_controls()
        self.path = tempfile.mktemp(suffix='.json')

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_save_writes_json_state(self):
        Load.save_game(self.controls, self.path)
        with open(self.path) as f:
            state = json.load(f)
        self.assertEqual(state['room'], 'intro')
        self.assertIn('inventory', state)
        self.assertIn('player', state)

    def test_load_restores_room(self):
        Load.save_game(self.controls, self.path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.controls.move('n')
            self.controls.move('e')
        self.assertEqual(self.controls.loc.id, 'cave')
        self.assertTrue(Load.load_game(self.controls, self.path))
        self.assertEqual(self.controls.loc.id, 'intro')
        self.assertEqual(self.controls.position, 'Forest Edge')

    def test_load_restores_inventory_and_player(self):
        self.controls.inventory.add('stone', 7)
        self.controls.Player.name = 'Hero'
        Load.save_game(self.controls, self.path)

        fresh = quiet_controls()
        Load.load_game(fresh, self.path)
        self.assertEqual(fresh.inventory.slots['stone'], 7)
        self.assertEqual(fresh.Player.name, 'Hero')

    def test_load_restores_dead_player(self):
        self.controls.Player.take_damage(self.controls.Player.health)
        Load.save_game(self.controls, self.path)

        fresh = quiet_controls()
        Load.load_game(fresh, self.path)
        self.assertFalse(fresh.Player.alive)
        self.assertEqual(fresh.Player.health, 0)
        with contextlib.redirect_stdout(io.StringIO()):
            fresh.move('n')
        self.assertEqual(fresh.loc.id, 'intro')

    def test_load_missing_save_returns_false(self):
        self.assertFalse(Load.load_game(self.controls, self.path))

    def test_do_save_and_do_load(self):
        c = self.controls
        with contextlib.redirect_stdout(io.StringIO()) as out:
            c.do_save('')
        self.assertIn('Game saved', out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            c.move('n')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            c.do_load('')
        self.assertIn('Game loaded', out.getvalue())
        self.assertEqual(c.loc.id, 'intro')
        if os.path.exists(Load.SAVE_FILE):
            os.remove(Load.SAVE_FILE)


if __name__ == '__main__':
    unittest.main()
