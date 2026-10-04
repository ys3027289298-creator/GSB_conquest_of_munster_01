"""Command table and parser tests.

Covers:
  * the command table itself (canonical keys, unique synonyms)
  * parsing consistency under mixed case and irregular whitespace
  * empty / blank / garbage input must not crash
"""
import unittest

from tests.helpers import SRC_DIR  # noqa: F401  (sets sys.path)

import commands


class CommandTableTest(unittest.TestCase):
    def test_canonical_keys(self):
        expected = {'quit', 'look', 'help', 'verbose', 'go', 'where',
                    'inventory', 'save', 'load'}
        self.assertEqual(expected, set(commands.commands.keys()))

    def test_synonyms_are_unique_across_table(self):
        seen = {}
        for canonical, synonyms in commands.commands.items():
            for word in synonyms:
                self.assertNotIn(
                    word, seen,
                    "synonym {!r} claimed by both {!r} and {!r}".format(
                        word, seen.get(word), canonical))
                seen[word] = canonical

    def test_synonyms_are_lowercase_single_words(self):
        for canonical, synonyms in commands.commands.items():
            self.assertTrue(synonyms, "empty synonym list for " + canonical)
            for word in synonyms:
                self.assertEqual(word, word.lower())
                self.assertNotIn(' ', word)


class ParseConsistencyTest(unittest.TestCase):
    """Bug reproduced: identical commands typed with different case or
    spacing must resolve to the same canonical command."""

    def test_case_insensitive(self):
        self.assertEqual(commands.parse('GO').action,
                         commands.parse('go').action)
        self.assertEqual(commands.parse('Look').action,
                         commands.parse('look').action)
        self.assertEqual(commands.parse('QUIT').action,
                         commands.parse('quit').action)

    def test_whitespace_insensitive(self):
        self.assertEqual(commands.parse('   go   ').action,
                         commands.parse('go').action)
        self.assertEqual(commands.parse('\tlook\n').action,
                         commands.parse('look').action)
        self.assertEqual(commands.parse('go    alpha')[:2],
                         commands.parse('go alpha')[:2])

    def test_synonyms_map_to_canonical(self):
        for canonical, synonyms in commands.commands.items():
            for word in synonyms:
                parsed = commands.parse(word)
                self.assertIsNotNone(parsed, "no parse for " + word)
                self.assertEqual(canonical, parsed.action)

    def test_extract_commands_legacy_interface(self):
        self.assertEqual('go', commands.extract_commands('GO'))
        self.assertEqual('look', commands.extract_commands('  ls  '))
        self.assertEqual('quit', commands.extract_commands('Goodbye!'))

    def test_target_extraction(self):
        parsed = commands.parse('go alpha')
        self.assertEqual('go', parsed.action)
        self.assertEqual('alpha', parsed.target)
        self.assertIsNone(commands.parse('look').target)

    def test_dotdot_target_survives_parsing(self):
        parsed = commands.parse('go ..')
        self.assertEqual('go', parsed.action)
        self.assertEqual('..', parsed.target)


class EmptyAndGarbageInputTest(unittest.TestCase):
    """Bug reproduced: empty input crashed / misbehaved."""

    def test_empty_string(self):
        self.assertIsNone(commands.parse(''))
        self.assertIsNone(commands.extract_commands(''))

    def test_whitespace_only(self):
        self.assertIsNone(commands.parse('   '))
        self.assertIsNone(commands.parse('\t\n '))

    def test_none_input(self):
        self.assertIsNone(commands.parse(None))
        self.assertIsNone(commands.extract_commands(None))

    def test_punctuation_only(self):
        self.assertIsNone(commands.parse('...'))
        self.assertIsNone(commands.parse('!@#$%^&*()'))

    def test_garbage_words(self):
        self.assertIsNone(commands.parse('xyzzy plugh'))
        self.assertIsNone(commands.extract_commands('xyzzy plugh'))

    def test_prioritize_empty_and_null(self):
        self.assertIsNone(commands.prioritize_commands(()))
        self.assertIsNone(commands.prioritize_commands(None))

    def test_prioritize_single_and_multi(self):
        self.assertEqual('go', commands.prioritize_commands(('go',)))
        self.assertEqual('quit',
                         commands.prioritize_commands(('go', 'quit')))


if __name__ == '__main__':
    unittest.main()
