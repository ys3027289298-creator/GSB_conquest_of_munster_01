from unittest import TestCase
from Parser import parseCommand


class Parser_parseCommand(TestCase):

    def test_parses_verb_and_argument(self):
        self.assertEqual(parseCommand('go north'), ('go', 'north'))

    def test_parses_verb_without_argument(self):
        self.assertEqual(parseCommand('look'), ('look', None))

    def test_verb_is_lowercase(self):
        self.assertEqual(parseCommand('TAKE key'), ('take', 'key'))

    def test_empty_command_raises(self):
        self.assertRaises(ValueError, parseCommand, '')
        self.assertRaises(ValueError, parseCommand, '   ')
        self.assertRaises(ValueError, parseCommand, None)

    def test_non_string_command_raises(self):
        self.assertRaises(ValueError, parseCommand, 5)
