import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'game'))

from room import Room, get_room, grab_object


def make_controls():
    import main
    with contextlib.redirect_stdout(io.StringIO()):
        return main.Controls()


class TestRoomData(unittest.TestCase):

    def test_intro_room_loads(self):
        room = get_room('intro')
        self.assertEqual(room.id, 'intro')
        self.assertTrue(room.description)
        self.assertIn('e', room.neighbors)

    def test_neighbor_missing_returns_none(self):
        room = get_room('intro')
        self.assertIsNone(room._neighbor('n'))
        self.assertEqual(room._neighbor('e'), 'town')

    def test_room_objects(self):
        room = get_room('intro')
        self.assertIsNotNone(room._objects('trees'))
        self.assertIsNone(room._objects('dragon'))
        self.assertNotEqual(grab_object(room, 'trees'), 0)
        self.assertEqual(grab_object(room, 'dragon'), 0)


class TestMovement(unittest.TestCase):

    def test_move_east_goes_exactly_one_room(self):
        controls = make_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_e('')
        self.assertEqual(controls.loc.id, 'town')

    def test_position_updates_after_room_switch(self):
        controls = make_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_e('')
        self.assertEqual(controls.position, controls.loc.name)
        self.assertEqual(controls.event.room, controls.loc.name)

    def test_blocked_direction_keeps_room(self):
        controls = make_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_n('')
        self.assertEqual(controls.loc.id, 'intro')

    def test_round_trip(self):
        controls = make_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_e('')
            controls.do_w('')
        self.assertEqual(controls.loc.id, 'intro')

    def test_dead_player_cannot_move(self):
        controls = make_controls()
        controls.player.take_damage(controls.player.hp)
        self.assertFalse(controls.player.is_alive())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            controls.do_e('')
        self.assertEqual(controls.loc.id, 'intro')
        self.assertIn('dead', out.getvalue())

    def test_chop_adds_wood_and_get_holds_it(self):
        controls = make_controls()
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_chop('')
        self.assertTrue(controls.inventory.has_item('wood'))
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_get('wood')
        self.assertEqual(controls.player.right_hand, 'wood')
        with contextlib.redirect_stdout(io.StringIO()):
            controls.do_e('')
            controls.do_chop('')
        self.assertEqual(controls.inventory.slots['wood'], 1)

    def test_get_unknown_item_does_not_crash(self):
        controls = make_controls()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            controls.do_get('dragon')
        self.assertIn('You do not have this item', out.getvalue())


if __name__ == '__main__':
    unittest.main()
