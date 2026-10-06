"""A slain enemy must be gone for good (bug #2): it is removed from the
spawn data, the enemy map and the visible map, it never takes another
enemy's spawn entry with it, and it can never be fought again."""
import random

from tests.helpers import (QuietTestCase, all_enemy_coords, fast_battle_clock,
                           make_game, make_game_main, place_player)

# movement delta -> direction key, and its opposite
DIRECTIONS = {-10: "w", 10: "s", -1: "a", 1: "d"}
OPPOSITE = {"w": "s", "s": "w", "a": "d", "d": "a"}
TERRAIN = {"/", "=", "^", "~", "#"}


class EnemyDeathTest(QuietTestCase):

    def setUp(self):
        super().setUp()
        self.game = make_game(0)
        self.game_main = make_game_main(self.game)
        # make the player strong enough to slay any enemy in one hit
        self.game.player.strength = 100000

    def step_onto(self, enemy_tile):
        """Find a free neighbour of the enemy and walk onto the enemy."""
        game = self.game
        for delta, direction in DIRECTIONS.items():
            neighbour = enemy_tile - delta
            if not (0 <= neighbour <= 99):
                continue
            if game.now_map.map[neighbour] in TERRAIN:
                continue
            if game.enemies_map[neighbour] != "a":
                continue
            if not game.check_possibility_to_move(neighbour, enemy_tile):
                continue
            place_player(game, neighbour)
            self.assertEqual(game.choose_direction(neighbour, direction), enemy_tile)
            return direction
        return None

    def reachable_enemy(self, group_index):
        for tile in self.game.enemies_spawn.enemies[group_index]:
            direction = self.step_onto(tile)
            if direction is not None:
                return tile, direction
        return None, None

    def slay(self, group_index):
        enemy_tile, direction = self.reachable_enemy(group_index)
        self.assertIsNotNone(enemy_tile, msg=f"no reachable enemy in group {group_index}")
        self.assertTrue(self.game.check_if_able_to_fight(enemy_tile))
        random.seed(1)
        with fast_battle_clock():
            self.game_main.battle(enemy_tile)
        self.assertEqual(self.game_main.dead, 0)
        return enemy_tile, direction

    def test_enemy_removed_from_every_structure_after_death(self):
        game = self.game
        enemy_tile, _ = self.slay(4)  # a wolf
        # removed from the spawn lists and from the enemy map
        self.assertNotIn(enemy_tile, all_enemy_coords(game))
        self.assertEqual(game.enemies_map[enemy_tile], "a")
        # it can never be fought again
        self.assertFalse(game.check_if_able_to_fight(enemy_tile))

    def test_enemy_icon_does_not_stay_on_map_after_death(self):
        game = self.game
        enemy_tile, direction = self.slay(5)  # a dwarf
        # walk back off the corpse tile: no enemy sign may reappear
        game.choose_direction(enemy_tile, OPPOSITE[direction])
        self.assertEqual(game.now_map.map[enemy_tile], "O")
        self.assertEqual(game.now_map.map.count("x"), 1)

    def test_killing_one_enemy_removes_exactly_one_enemy(self):
        game = self.game
        before = [list(group) for group in game.enemies_spawn.enemies]
        # if two spawn groups share a tile (the old duplicate-spawn bug),
        # slaying the enemy there must still remove only one spawn entry
        counts = {}
        for group in before:
            for coord in group:
                counts[coord] = counts.get(coord, 0) + 1
        enemy_tile = None
        for coord, amount in counts.items():
            if amount > 1 and self.step_onto(coord) is not None:
                enemy_tile = coord
                break
        if enemy_tile is None:
            enemy_tile, _ = self.reachable_enemy(6)  # a cobra
        self.assertIsNotNone(enemy_tile)
        random.seed(1)
        with fast_battle_clock():
            self.game_main.battle(enemy_tile)
        self.assertEqual(self.game_main.dead, 0)
        after = game.enemies_spawn.enemies
        self.assertEqual(len(all_enemy_coords(game)), 40)
        changed = [i for i in range(len(before)) if before[i] != after[i]]
        # exactly one spawn group lost exactly this one coordinate
        self.assertEqual(len(changed), 1)
        self.assertEqual(before[changed[0]].count(enemy_tile), 1)
        self.assertNotIn(enemy_tile, after[changed[0]])

    def test_giant_quest_not_completed_by_other_deaths(self):
        game = self.game
        target_groups = [0, 1, 2, 4, 5, 6, 7]
        kills = 0
        # some enemies only become reachable after their neighbours die,
        # so keep slaying whatever is reachable until nothing else is
        while True:
            for group_index in target_groups:
                enemy_tile, _ = self.reachable_enemy(group_index)
                if enemy_tile is not None:
                    break
            else:
                break
            self.assertTrue(game.check_if_able_to_fight(enemy_tile))
            random.seed(1 + kills)
            with fast_battle_clock():
                self.game_main.battle(enemy_tile)
            self.assertEqual(self.game_main.dead, 0)
            kills += 1
        self.assertGreaterEqual(kills, 7)
        # the giant is untouched and the main quest is still open
        self.assertEqual(len(game.enemies_spawn.enemies[3]), 1)
        giant_tile = game.enemies_spawn.enemies[3][0]
        self.assertEqual(game.enemies_map[giant_tile].name, "Giant")
