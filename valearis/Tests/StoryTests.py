from unittest.case import TestCase
from Story import Story, NarrativeNode, NarrativeLoopError


def buildLinearStory():
    start = NarrativeNode('start', 'beginning')
    middle = NarrativeNode('middle', 'middle')
    end = NarrativeNode('end', 'end')
    start.addChoice('go', middle)
    middle.addChoice('go', end)
    return start, middle, end


class NarrativeNodeTests(TestCase):

    def test_nodeWithoutNameRaises(self):
        self.assertRaises(ValueError, NarrativeNode, None)
        self.assertRaises(ValueError, NarrativeNode, '')

    def test_choiceWithoutLabelOrNodeRaises(self):
        node = NarrativeNode('a')
        self.assertRaises(ValueError, node.addChoice, '', NarrativeNode('b'))
        self.assertRaises(ValueError, node.addChoice, 'next', None)

    def test_unknownChoiceRaises(self):
        node = NarrativeNode('a')
        self.assertRaises(KeyError, node.choice, 'nope')

    def test_linearStoryWalksToEnd(self):
        start, middle, end = buildLinearStory()
        story = Story(start)
        self.assertIs(story.walk(['go', 'go']), end)

    def test_loopRaisesAndStopsAtSafeNode(self):
        start = NarrativeNode('start')
        middle = NarrativeNode('middle')
        start.addChoice('next', middle)
        middle.addChoice('back', start)
        story = Story(start)
        story.choose('next')
        self.assertRaises(NarrativeLoopError, story.choose, 'back')
        self.assertEqual(story.current.name, 'middle')

    def test_selfLoopRaises(self):
        node = NarrativeNode('self')
        node.addChoice('again', node)
        story = Story(node)
        self.assertRaises(NarrativeLoopError, story.choose, 'again')

    def test_resetReturnsToStart(self):
        start, middle, end = buildLinearStory()
        story = Story(start)
        story.walk(['go', 'go'])
        story.reset()
        self.assertIs(story.current, start)


class StoryStateTests(TestCase):

    def test_stateRoundTrip(self):
        start, middle, end = buildLinearStory()
        story = Story(start)
        story.walk(['go', 'go'])
        data = story.to_dict()
        restored = Story(buildLinearStory()[0])
        restored.loadState(data)
        self.assertEqual(restored.current.name, 'end')

    def test_loadStateMissingFieldRaises(self):
        story = Story(NarrativeNode('a'))
        self.assertRaises(ValueError, story.loadState, {})
        self.assertRaises(ValueError, story.loadState, 'nope')

    def test_loadStateUnknownNodeRaises(self):
        story = Story(NarrativeNode('a'))
        self.assertRaises(KeyError, story.loadState, {'current': 'ghost'})

    def test_branchingStoryKeepsDistinctPaths(self):
        root = NarrativeNode('root')
        left = NarrativeNode('left')
        right = NarrativeNode('right')
        root.addChoice('left', left)
        root.addChoice('right', right)
        story = Story(root)
        self.assertIs(story.choose('left'), left)
        story.reset()
        self.assertIs(story.choose('right'), right)
