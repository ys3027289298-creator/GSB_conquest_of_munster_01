"""世界状态迁移: save/load of player state, object location and event flags."""
from tests.util import GameTestCase

from pyquest.errors import MissingObjectError



class PlayerStateTests(GameTestCase):
    def test_save_load_roundtrip_restores_attributes(self):
        self.player.gold = 99
        state = self.game.save_state()
        self.player.gold = 0
        self.game.load_state(state)
        self.assertEqual(str(self.game.objects["player"].gold), "99")

    def test_load_removes_attributes_added_after_save(self):
        state = self.game.save_state()
        self.player.lucky_charm = "rabbit foot"
        self.game.load_state(state)
        self.assertNotIn("lucky_charm", self.game.objects["player"].__dict__)

    def test_object_location_is_saved(self):
        sword = self.game.objects["sword"]
        hall = self.game.objects["hall"]
        state = self.game.save_state()
        sword.parent = hall
        self.game.load_state(state)
        self.assertIs(self.game.objects["sword"].parent, self.game.objects["cave"])

    def test_object_location_migration_persists_in_new_save(self):
        sword = self.game.objects["sword"]
        sword.parent = self.game.objects["hall"]
        state = self.game.save_state()
        sword.parent = self.game.objects["cave"]
        self.game.load_state(state)
        self.assertIs(self.game.objects["sword"].parent, self.game.objects["hall"])

    def test_firsttime_flags_are_saved(self):
        self.call_function("EnterHall")
        state = self.game.save_state()
        self.game.script_engine.firsttime_done.clear()
        self.game.load_state(state)
        _, out = self.call_function("EnterHall")
        self.assertIn("again", out)

    def test_load_state_with_unknown_object_fails(self):
        state = self.game.save_state()
        state["objects"]["ghost"] = {"gold": 1}
        with self.assertRaises(MissingObjectError):
            self.game.load_state(state)

    def test_snapshot_contains_only_plain_data(self):
        state = self.game.save_state()
        for name, attributes in state["objects"].items():
            for key, value in attributes.items():
                self.assertIsInstance(value, (str, int, float, bool, list, type(None)),
                                      "%s.%s is not plain data" % (name, key))
