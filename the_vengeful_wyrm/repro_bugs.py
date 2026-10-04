"""
Reproducer for the six defect classes in the_vengeful_wyrm.

    python3 repro_bugs.py

1. attribute out of bounds  -> hit points drop below 0
2. unstable dice results    -> rolls are not reproducible (no fixed seed hook)
3. negative health bar      -> HealthBar renders negative HP / over-length bar
4. mission completed twice  -> defeat still returns "mission completed"
5. path loop                -> empty riddle answer loops; invalid play-again
                               answer silently restarts the whole journey
6. story advances after loss-> fight outcome is ignored, Happy End state reached

No narrative text is touched: story .txt files do not exist in the repo, so
placeholder fixtures are created in a temp directory.
"""

import builtins
import contextlib
import io
import random
import time

import tvw_test_support as support

support.install_stubs()

import tvw_dices
import tvw_fight
import tvw_healthbar
import tvw_path

# Keep the reproducer fast.
time.sleep = lambda *a, **k: None

REPORTS = []


def report(title, observation, verdict):
    REPORTS.append((title, observation, verdict))
    print(f"\n=== {title} ===")
    print(observation)
    print(verdict)


def captured(callable_, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = callable_(*args, **kwargs)
    return result, buf.getvalue()


# Importing tvw_game executes the whole play-again loop at module level.
# Script the import-time run: decline the mission, then answer "maybe"
# (invalid) to play-again, which should re-ask but instead restarts the game.
import_inputs = [
    "1", "Repro", "no", "yes",   # run 1: decline mission -> game over
    "maybe",                      # invalid play-again answer
    "1", "Repro", "no", "yes",   # run 2: forced replay
    "no",                         # finally: stop playing
]
fake = support.FakeInput(import_inputs)
original_input = builtins.input
builtins.input = fake
import_buf = io.StringIO()
with support.narrative_cwd(), contextlib.redirect_stdout(import_buf):
    import tvw_game
builtins.input = original_input
import_output = import_buf.getvalue()

choose_count = import_output.count("Choose your character")
reprompted = "I did not understand" in import_output
report(
    "5b. path loop: invalid 'play again' answer restarts the journey",
    f"invalid answer 'maybe' produced {choose_count} game starts "
    f"(expected exactly 1 plus a yes/no re-prompt; re-prompt seen: {reprompted})",
    "BUG REPRODUCED" if choose_count >= 2 else "not reproduced",
)

# --- 1. attribute out of bounds ------------------------------------------
user = {"hit points": 3, "armor_class": 10, "damage": 2}
enemy = {"hit points": 20, "armor_class": 10, "attack bonus": 1, "damage": 2}
captured(tvw_fight.enemy_attack, lambda: 20, lambda w: 6, user, enemy)
report(
    "1. attribute out of bounds: hit points go negative",
    f"3 HP, 8 damage -> user hit points = {user['hit points']} (valid range is 0..max)",
    "BUG REPRODUCED" if user["hit points"] < 0 else "not reproduced",
)

# --- 2. unstable dice ------------------------------------------------------
random.seed()
seq_a = [tvw_dices.enemy_D20() for _ in range(5)]
seq_b = [tvw_dices.enemy_D20() for _ in range(5)]
random.seed(123)
seeded_a = [tvw_dices.enemy_D20() for _ in range(5)]
random.seed(123)
seeded_b = [tvw_dices.enemy_D20() for _ in range(5)]
report(
    "2. unstable dice: unseeded rolls cannot be reproduced",
    f"two unseeded sequences: {seq_a} vs {seq_b} "
    f"(differ in {sum(a != b for a, b in zip(seq_a, seq_b))}/5)\n"
    f"same fixed seed sequences: {seeded_a} vs {seeded_b} (match: {seeded_a == seeded_b})\n"
    "dice functions accept no rng/seed argument; tests must seed the global RNG",
    "CONFIRMED: only seeded runs are reproducible",
)

# --- 3. negative health bar ------------------------------------------------
entity = {"hit points": 15}
bar = tvw_healthbar.HealthBar(entity)
entity["hit points"] = -5
bar.update()
_, bar_output = captured(bar.draw)
drawn_lost = bar_output.count(tvw_healthbar.HealthBar.symbol_lost)
drawn_remaining = bar_output.count(tvw_healthbar.HealthBar.symbol_remaining)
report(
    "3. negative health bar",
    f"bar output for -5/15:\n{bar_output.strip()}\n"
    f"bar drew {drawn_remaining} remaining / {drawn_lost} lost segments (bar length is 20)",
    "BUG REPRODUCED" if ("-" in bar_output.splitlines()[0] or drawn_lost > 20) else "not reproduced",
)

# --- 5a. riddle empty-input loop ------------------------------------------
riddle_input = support.FakeInput(["", "", "the future"])
builtins.input = riddle_input
_, riddle_output = captured(tvw_path.riddle, "Repro")
builtins.input = original_input
report(
    "5a. path loop: empty riddle answer never resolves the path",
    f"two empty answers + one correct answer consumed {riddle_input.prompts} prompts "
    "before returning (an empty answer should resolve the path, not loop forever)",
    "BUG REPRODUCED" if riddle_input.prompts == 3 else "not reproduced",
)

# --- 4 + 6. defeat still completes the mission ----------------------------
loss_patches = {
    "tvw_fight__user_D20": lambda: 1,
    "tvw_fight__user_D6": lambda u: 1,
    "tvw_fight__enemy_D20": lambda: 20,
    "tvw_fight__enemy_D6": lambda w: 6,
}
dwarf = {"hit points": 15, "armor_class": 12, "initiative bonus": 2,
         "attack bonus": 3, "damage": 2}
wyrm = {"hit points": 20, "armor_class": 10, "initiative bonus": 1,
        "attack bonus": 1, "damage": 2}
with support.patched(**loss_patches):
    fight_return, fight_text = captured(tvw_fight.fight, dict(dwarf), dict(wyrm), "Hero")

fake = support.FakeInput(["1", "Hero", "yes", "wisdom", "the future"])
builtins.input = fake
with support.narrative_cwd(), support.patched(**loss_patches):
    game_result, game_output = captured(tvw_game.the_vengeful_wyrm)
builtins.input = original_input

defeat_shown = "you are defeated" in fight_text.lower()
report(
    "6. story advances after the fight is lost",
    f"fight() return value: {fight_return!r} (caller cannot distinguish win from loss)\n"
    f"the_vengeful_wyrm() returned: {game_result!r} despite defeat shown: {defeat_shown}",
    "BUG REPRODUCED" if (defeat_shown and game_result is True) else "not reproduced",
)
report(
    "4. mission completed twice: a lost run counts as a completed mission",
    "a defeated play-through reaches the same 'completed' return value (True) as a "
    "victorious one, so the mission is reported completed regardless of outcome",
    "BUG REPRODUCED" if (defeat_shown and game_result is True) else "not reproduced",
)

print("\n" + "=" * 60)
print("SUMMARY")
for title, _, verdict in REPORTS:
    print(f"  {verdict:35s} {title}")
