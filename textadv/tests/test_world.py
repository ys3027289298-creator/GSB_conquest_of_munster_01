"""Tests for textadv.gamesystem.world and textadv.gamesystem.relations:
properties, relations, world.copy, and serialize/deserialize state
consistency."""

import unittest

from tests import *  # noqa: F401,F403  (sets up sys.path)

from textadv.gamesystem.world import World, Property
from textadv.gamesystem.relations import (ManyToOneRelation, OneToManyRelation,
                                          ManyToManyRelation, FreeformRelation)
from textadv.gamesystem.basicpatterns import X, Y, Z
from textadv.gamesystem.utilities import list_append


class Contains(OneToManyRelation) :
    """Contains(x, y): x contains y."""
class KindOf(ManyToOneRelation) :
    """KindOf(x, y): x is a direct subkind of y."""
class Knows(ManyToManyRelation) :
    """Knows(x, y): x knows y (commutative)."""
class Exit(FreeformRelation) :
    """Exit(room, direction, room)."""
    def __init__(self, *args) :
        self.args = args


def make_world() :
    world = World()

    @world.define_property
    class Global(Property) :
        numargs = 1

    @world.define_property
    class Size(Property) :
        numargs = 1

    world[Global("game_started")] = False
    world[Size("ball")] = 3

    world.define_relation(Contains)
    world.define_relation(KindOf)
    world.define_relation(Knows)
    world.define_relation(Exit)
    return world


class TestProperties(unittest.TestCase) :
    def test_set_get_before_game_defined(self) :
        world = make_world()
        self.assertEqual(world[world.property_types["Size"]("ball")], 3)
        self.assertEqual(world.get_property("Size", "ball"), 3)

    def test_modified_properties_after_game_defined(self) :
        """After the game is defined, writes go to the modified
        properties table and read back correctly."""
        world = make_world()
        world.set_game_defined()
        Size = world.property_types["Size"]
        world[Size("ball")] = 5
        self.assertEqual(world[Size("ball")], 5)
        self.assertIn(Size("ball"), world.modified_properties)
        world.set_property("Size", "ball", value=7)
        self.assertEqual(world.get_property("Size", "ball"), 7)

    def test_missing_property_raises(self) :
        world = make_world()
        Size = world.property_types["Size"]
        self.assertRaises(KeyError, world.__getitem__, Size("nonexistent"))


class TestRelations(unittest.TestCase) :
    def test_add_query_remove(self) :
        world = make_world()
        world.add_relation(Contains("box", "ball"))
        self.assertEqual(world.query_relation(Contains("box", X), var=X), ["ball"])
        self.assertEqual(world.query_relation(Contains("box", "ball")), [{}])
        world.remove_relation(Contains(Z, "ball"))
        self.assertEqual(world.query_relation(Contains("box", X), var=X), [])

    def test_many_to_one_uniqueness(self) :
        world = make_world()
        world.add_relation(KindOf("container", "thing"))
        self.assertRaises(Exception, world.add_relation, KindOf("container", "entity"))

    def test_many_to_many_commutative(self) :
        world = make_world()
        world.add_relation(Knows("alice", "bob"))
        self.assertEqual(world.query_relation(Knows("bob", X), var=X), ["alice"])
        self.assertEqual(world.query_relation(Knows("alice", X), var=X), ["bob"])

    def test_freeform_relation(self) :
        world = make_world()
        world.add_relation(Exit("kitchen", "north", "hall"))
        self.assertEqual(world.query_relation(Exit("kitchen", X, Y)),
                         [{"x" : "north", "y" : "hall"}])

    def test_path_to(self) :
        world = make_world()
        world.add_relation(KindOf("container", "thing"))
        world.add_relation(KindOf("thing", "kind"))
        self.assertEqual(world.r_path_to(KindOf, "container", "kind"),
                         ["container", "thing", "kind"])
        self.assertIsNone(world.r_path_to(KindOf, "kind", "container"))

    def test_path_to_reflexive_after_caching(self) :
        """The path_to cache must be keyed by the *start* node; a
        cached path a->...->b must not corrupt the reflexive query
        path_to(b, b)."""
        world = make_world()
        world.add_relation(KindOf("container", "thing"))
        world.add_relation(KindOf("thing", "kind"))
        # populate the cache with a path ending at "kind"
        self.assertEqual(world.r_path_to(KindOf, "container", "kind"),
                         ["container", "thing", "kind"])
        # reflexive queries must still be trivial
        self.assertEqual(world.r_path_to(KindOf, "kind", "kind"), ["kind"])
        self.assertEqual(world.r_path_to(KindOf, "thing", "thing"), ["thing"])
        # and the cached path is still correct
        self.assertEqual(world.r_path_to(KindOf, "container", "kind"),
                         ["container", "thing", "kind"])


class TestCopy(unittest.TestCase) :
    def test_copy_relation_isolation(self) :
        world = make_world()
        world.add_relation(Contains("box", "ball"))
        copied = world.copy()
        copied.add_relation(Contains("box", "key"))
        self.assertEqual(world.query_relation(Contains("box", X), var=X), ["ball"])
        self.assertEqual(sorted(copied.query_relation(Contains("box", X), var=X)),
                         ["ball", "key"])

    def test_copy_modified_properties_isolation(self) :
        world = make_world()
        world.set_game_defined()
        Size = world.property_types["Size"]
        world[Size("ball")] = 9
        copied = world.copy()
        copied[Size("ball")] = 12
        self.assertEqual(world[Size("ball")], 9)
        self.assertEqual(copied[Size("ball")], 12)

    def test_copy_activity_isolation(self) :
        world = make_world()
        world.define_activity("mark", accumulator=list_append)

        @world.to("mark")
        def _mark(world) :
            return ["orig"]

        copied = world.copy()

        @copied.to("mark")
        def _mark2(world) :
            return ["copied-only"]

        self.assertEqual(world.activity.mark(), ["orig"])
        self.assertEqual(copied.activity.mark(), ["orig", "copied-only"])


class TestSerialize(unittest.TestCase) :
    def make_defined_world(self) :
        world = make_world()
        world.define_activity("put_in")

        @world.to("put_in")
        def _put_in(x, y, world) :
            world.add_relation(Contains(y, x))

        world.define_activity("mark")

        @world.to("mark")
        def _mark(world) :
            return None

        world.set_game_defined()
        Global = world.property_types["Global"]
        Size = world.property_types["Size"]
        world[Global("score")] = 10
        world[Size("ball")] = 42
        world.add_relation(Contains("box", "ball"))
        world.add_relation(KindOf("container", "thing"))
        return world

    def test_round_trip_properties(self) :
        world = self.make_defined_world()
        restored = world.deserialize(world.serialize())
        self.assertEqual(restored.get_property("Global", "score"), 10)
        self.assertEqual(restored.get_property("Size", "ball"), 42)

    def test_round_trip_relations(self) :
        world = self.make_defined_world()
        restored = world.deserialize(world.serialize())
        self.assertEqual(restored.query_relation(Contains("box", X), var=X), ["ball"])
        self.assertEqual(restored.r_path_to(KindOf, "container", "thing"),
                         ["container", "thing"])

    def test_round_trip_drops_stale_cache(self) :
        """A polluted path_to cache must not survive serialization:
        the deserialized world's queries must be computed from the
        actual relation data."""
        world = self.make_defined_world()
        world.add_relation(KindOf("thing", "kind"))
        world.r_path_to(KindOf, "container", "kind")
        restored = world.deserialize(world.serialize())
        self.assertEqual(restored.r_path_to(KindOf, "kind", "kind"), ["kind"])
        self.assertEqual(restored.r_path_to(KindOf, "container", "kind"),
                         ["container", "thing", "kind"])

    def test_deserialized_world_activities_write_to_itself(self) :
        """Activities invoked on the deserialized world must see and
        modify the deserialized world, not the world it was
        deserialized from (regression: the activity helper stayed
        bound to the original world)."""
        world = self.make_defined_world()
        restored = world.deserialize(world.serialize())
        restored.activity.put_in("key", "box")
        self.assertEqual(sorted(restored.query_relation(Contains("box", X), var=X)),
                         ["ball", "key"])
        # the original world is unchanged:
        self.assertEqual(world.query_relation(Contains("box", X), var=X), ["ball"])

    def test_deserialized_world_activities_dict_not_shared(self) :
        world = self.make_defined_world()
        restored = world.deserialize(world.serialize())
        self.assertIsNot(restored._activities, world._activities)
        # but the handlers are still available:
        restored.activity.mark()

    def test_deserialized_world_activity_helper_bound_to_self(self) :
        world = self.make_defined_world()
        restored = world.deserialize(world.serialize())
        self.assertIs(restored.activity.__handler__, restored)


if __name__ == "__main__" :
    unittest.main()
