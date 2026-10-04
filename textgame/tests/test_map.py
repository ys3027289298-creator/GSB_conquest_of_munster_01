import contextlib
import io
import unittest

import tests  # noqa: F401  sets up sys.path
from main import Controls
from room import Room, get_room, grab_object


def quiet_controls():
    with contextlib.redirect_stdout(io.StringIO()):
        return Controls()


class RoomLoadingTest(unittest.TestCase):

    def test_get_room_loads_data(self):
        room = get_room('intro')
        self.assertEqual(room.id, 'intro')
        self.assertEqual(room.name, 'Forest Edge')
        self.assertIn('n', room.neighbors)

    def test_neighbor_missing_direction(self):
        room = get_room('intro')
        self.assertIsNone(room._neighbor('w'))
        self.assertEqual(room._neighbor('n'), 'hall')

    def test_grab_object(self):
        room = get_room('intro')
        self.assertIsNone(grab_object(room, 'jetpack'))


class MovementTest(unittest.TestCase):

    def test_move_updates_location_and_position(self):
        c = quiet_controls()
        self.assertEqual(c.position, 'Forest Edge')
        with contextlib.redirect_stdout(io.StringIO()):
            c.move('n')
        self.assertEqual(c.loc.id, 'hall')
        self.assertEqual(c.position, c.loc.name)

    def test_move_blocked_keeps_state(self):
        c = quiet_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            c.move('w')
        self.assertEqual(c.loc.id, 'intro')
        self.assertEqual(c.position, 'Forest Edge')

    def test_do_e_moves_once(self):
        c = quiet_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            c.move('n')
            c.do_e('')
        self.assertEqual(c.loc.id, 'cave')
        self.assertEqual(c.position, c.loc.name)

    def test_dead_player_cannot_move(self):
        c = quiet_controls()
        c.Player.take_damage(c.Player.health)
        self.assertFalse(c.Player.alive)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            c.move('n')
        self.assertEqual(c.loc.id, 'intro')
        self.assertIn('dead', out.getvalue())

    def test_do_get_unknown_item(self):
        c = quiet_controls()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            c.do_get('jetpack')
        self.assertIn('do not have', out.getvalue())


if __name__ == '__main__':
    unittest.main()
