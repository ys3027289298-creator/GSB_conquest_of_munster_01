'''Covers the command table: synonym resolution, case/space handling,
prioritization, and the behavior of each command executor.'''
import pytest

import commands as c


class TestCommandTable:
    def test_every_synonym_resolves_to_its_canonical_command(self):
        for canonical, synonyms in c.commands.items():
            for word in synonyms:
                assert c.extract_commands(word) == canonical

    def test_every_canonical_command_has_a_handler(self):
        for canonical in c.commands:
            if canonical == 'where':
                # 'where' is intentionally a placeholder handled inline
                continue
            assert callable(getattr(c, 'execute_{}'.format(canonical))), canonical

    def test_synonym_lists_do_not_overlap(self):
        seen = {}
        for canonical, synonyms in c.commands.items():
            for word in synonyms:
                assert word not in seen, '{} mapped to both {} and {}'.format(
                    word, seen.get(word), canonical)
                seen[word] = canonical


class TestCommandParsing:
    def test_uppercase_input(self):
        assert c.extract_commands('LOOK') == 'look'
        assert c.extract_commands('Quit') == 'quit'
        assert c.extract_commands('CD') == 'go'

    def test_leading_trailing_and_internal_whitespace(self):
        assert c.extract_commands('   look   ') == 'look'
        assert c.extract_commands('\t  go  \n') == 'go'

    def test_mixed_case_with_extra_spaces(self):
        assert c.extract_commands('   HeLp   ') == 'help'
        assert c.extract_commands('  ExIt ') == 'quit'

    def test_punctuation_is_stripped(self):
        assert c.extract_commands('look!') == 'look'
        assert c.extract_commands('...quit...') == 'quit'

    def test_unrecognized_words_return_none(self):
        assert c.extract_commands('flibbertigibbet') is None
        assert c.extract_commands('12345') is None

    def test_empty_and_whitespace_input_return_none(self):
        # Reproduces: empty command used to crash (str.translate(None, ...)
        # is a TypeError on Python 3).
        assert c.extract_commands('') is None
        assert c.extract_commands('   ') is None
        assert c.extract_commands('\n\t ') is None
        assert c.extract_commands(None) is None

    def test_multiple_commands_are_prioritized(self):
        assert c.extract_commands('look then quit') == 'quit'
        assert c.extract_commands('go and help') == 'help'

    def test_prioritize_single_and_empty(self):
        assert c.prioritize_commands(('look',)) == 'look'
        assert c.prioritize_commands(()) is None

    def test_prioritize_where_does_not_crash(self):
        # Reproduces: 'where' was missing from priority_order, so
        # priority_order.index('where') raised ValueError.
        assert c.prioritize_commands(('where',)) == 'where'
        assert c.prioritize_commands(('where', 'look')) == 'look'
        assert c.prioritize_commands(('go', 'where')) == 'go'


class TestExecuteCommands:
    def test_quit_exits(self):
        with pytest.raises(SystemExit):
            c.execute_command('quit')

    def test_where_is_still_a_placeholder(self, capsys):
        c.execute_command('where')
        out = capsys.readouterr().out
        assert "Haha, this is embarrassing, I haven't coded that yet." in out

    def test_unknown_action_is_handled_gracefully(self, capsys):
        c.execute_command('frobnicate')
        assert "Sorry! I don't know what to tell you." in capsys.readouterr().out

    def test_look_lists_real_directory_without_state(self, fs_tree, capsys):
        c.execute_look(path=str(fs_tree))
        out = capsys.readouterr().out
        assert 'You see some files:' in out
        assert 'README.txt' in out
        assert 'castle' in out

    def test_look_empty_directory(self, tmp_path, capsys):
        c.execute_look(path=str(tmp_path))
        out = capsys.readouterr().out
        assert 'There are no files here.' in out
        assert 'You can go: back the way you came' in out

    def test_go_without_target_prints_the_prompt(self, fs_tree, capsys):
        import narrator as n
        state = n.GameState(str(fs_tree))
        c.execute_command('go', 'go', state=state)
        out = capsys.readouterr().out
        assert "Where do you want to move?" in out
        assert 'castle' in out

    def test_format_list_returns_multiline_text(self):
        text = c.format_list(['alpha', 'beta', 'gamma', 'delta', 'epsilon'], column_num=2)
        for name in ('alpha', 'beta', 'gamma', 'delta', 'epsilon'):
            assert name in text
        assert text.count('\n') == 2

    def test_format_list_empty(self):
        assert c.format_list([]) == ''
