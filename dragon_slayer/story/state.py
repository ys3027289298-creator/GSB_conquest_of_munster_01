"""Story node state machine.

Stages advance in the intended order: intro -> training -> fishing ->
battle -> victory. Defeat routes to game_over instead of falling through
to the next story node.
"""

INTRO = "intro"
TRAINING = "training"
FISHING = "fishing"
BATTLE = "battle"
VICTORY = "victory"
GAME_OVER = "game_over"

ORDER = [INTRO, TRAINING, FISHING, BATTLE]


def next_stage(stage):
    """Return the story node that follows a completed stage."""
    index = ORDER.index(stage)
    return ORDER[index + 1] if index + 1 < len(ORDER) else VICTORY


def after_battle(won):
    """Route the story after the dragon fight based on the result."""
    return VICTORY if won else GAME_OVER
