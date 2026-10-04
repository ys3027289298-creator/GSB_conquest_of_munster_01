import builtins
import contextlib
import io
import os
from unittest import mock

import story.state as state_mod
import story.fishing as fishing_mod
import story.battle as battle_mod


class InputScript:
    def __init__(self, lines):
        self.lines = list(lines)

    def __call__(self, prompt=""):
        if not self.lines:
            raise AssertionError(f"input script exhausted at prompt: {prompt!r}")
        print(prompt, end="")
        return self.lines.pop(0)


@contextlib.contextmanager
def patched_game(inputs, save_path, fish_items=(), dragon_abilities=("Claw",)):
    fish_iter = iter(fish_items)
    dragon_iter = iter(dragon_abilities)
    dragon_fallback = [dragon_abilities[-1] if dragon_abilities else "Claw"]

    def next_fish():
        return next(fish_iter)

    def next_dragon(dragon):
        try:
            dragon_fallback[0] = next(dragon_iter)
        except StopIteration:
            pass
        return dragon_fallback[0]

    with mock.patch.object(state_mod, "DEFAULT_SAVE_PATH", save_path), \
         mock.patch.object(builtins, "input", InputScript(inputs)), \
         mock.patch("time.sleep", lambda *args, **kwargs: None), \
         mock.patch.object(fishing_mod, "get_random_item", next_fish), \
         mock.patch.object(battle_mod, "get_dragon_ability", next_dragon):
        yield save_path


def run_main(inputs, save_path, **kwargs):
    import main as main_mod

    output = io.StringIO()
    with patched_game(inputs, save_path, **kwargs):
        with contextlib.redirect_stdout(output):
            main_mod.main()
    return output.getvalue()
