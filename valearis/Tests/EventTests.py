from unittest import TestCase
from Area import Area
from Game import Game


class Game_events(TestCase):

    def test_event_runs_action_on_first_trigger(self):
        game = Game(Area('hall', 'a hall'))
        calls = []
        game.on('alarm', lambda game, event: calls.append(event))

        self.assertTrue(game.trigger('alarm'))
        self.assertEqual(calls, ['alarm'])
        self.assertTrue(game.hasTriggered('alarm'))

    def test_event_runs_only_once(self):
        game = Game(Area('hall', 'a hall'))
        calls = []
        game.on('alarm', lambda game, event: calls.append(event))

        game.trigger('alarm')
        self.assertFalse(game.trigger('alarm'))

        self.assertEqual(calls, ['alarm'])

    def test_multiple_actions_run_once(self):
        game = Game(Area('hall', 'a hall'))
        calls = []
        game.on('alarm', lambda game, event: calls.append('a'))
        game.on('alarm', lambda game, event: calls.append('b'))

        game.trigger('alarm')
        game.trigger('alarm')

        self.assertEqual(calls, ['a', 'b'])

    def test_independent_events_each_run_once(self):
        game = Game(Area('hall', 'a hall'))
        calls = []
        game.on('alarm', lambda game, event: calls.append('alarm'))
        game.on('bell', lambda game, event: calls.append('bell'))

        game.trigger('alarm')
        game.trigger('bell')

        self.assertEqual(calls, ['alarm', 'bell'])

    def test_registration_validates_arguments(self):
        game = Game(Area('hall', 'a hall'))

        self.assertRaises(ValueError, game.on, '', lambda game, event: None)
        self.assertRaises(ValueError, game.on, 'alarm', 'not callable')
        self.assertRaises(ValueError, game.trigger, '')
        self.assertRaises(ValueError, game.trigger, '   ')
