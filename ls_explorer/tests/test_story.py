"""Story-trigger tests.

Bug reproduced: the same command re-ran in the same place re-triggered
the narrative every time. A first-visit event must fire exactly once.
"""
from tests.helpers import SandboxCase, run_silently

import commands
import narrator


class StoryTriggerTest(SandboxCase):
    def test_story_fires_on_first_visit_only(self):
        state = narrator.GameState(self.root)

        _, first_output = run_silently(
            commands.execute_command, 'go', state, 'go alpha', 'alpha')
        self.assertIn(commands.STORY_FIRST_VISIT.split('{')[0], first_output)
        self.assertIn('enter:' + state.vfs.cwd, state.seen)

        run_silently(commands.execute_command, 'go', state, 'go ..', '..')
        _, second_output = run_silently(
            commands.execute_command, 'go', state, 'go alpha', 'alpha')
        self.assertNotIn(commands.STORY_FIRST_VISIT.split('{')[0],
                         second_output)

    def test_repeated_look_does_not_trigger_story(self):
        state = narrator.GameState(self.root)
        outputs = []
        for _ in range(3):
            _, text = run_silently(commands.execute_command, 'look', state,
                                   'look', None)
            outputs.append(text)
        self.assertTrue(all(t == outputs[0] for t in outputs))
        self.assertEqual(set(), state.seen)

    def test_failed_go_does_not_trigger_story(self):
        state = narrator.GameState(self.root)
        run_silently(commands.execute_command, 'go', state, 'go nowhere',
                     'nowhere')
        self.assertEqual(set(), state.seen)


if __name__ == '__main__':
    unittest.main()
