from story.intro import intro
from story.training import training
from story.fishing import fishing
from story.battle import battle
from story.state import (
    INTRO,
    TRAINING,
    FISHING,
    BATTLE,
    VICTORY,
    GAME_OVER,
    next_stage,
    after_battle,
)
import savegame
import time

def main():
    playing = True
    while playing:
        if savegame.has_saved_game():
            choice = get_title_choice()
        else:
            choice = "n"
        if choice == "c":
            player, stage = savegame.load_game()
        else:
            player = intro()
            stage = INTRO
            savegame.save_game(player, stage)
        stage = run_story(player, stage)
        if stage == VICTORY:
            savegame.clear_save()
            playing = play_again()
        else:
            playing = ask_quit_or_continue()
    print("\nThanks for playing!\n")

def get_title_choice():
    while True:
        time.sleep(1)
        choice = input("Continue saved game or start a new game? [c/n] ")
        if choice in ("c", "n"):
            return choice
        print("Enter c or n.")

STAGE_HANDLERS = {
    TRAINING: training,
    FISHING: fishing,
}

def run_story(player, stage):
    if stage == INTRO:
        stage = next_stage(INTRO)
        savegame.save_game(player, stage)
    if stage == GAME_OVER:
        revive_for_retry(player)
        stage = BATTLE
        savegame.save_game(player, stage)
    for node in (TRAINING, FISHING, BATTLE):
        if stage == node:
            if node == BATTLE:
                won = battle(player)
                stage = after_battle(won)
            else:
                STAGE_HANDLERS[node](player)
                stage = next_stage(node)
            savegame.save_game(player, stage)
            if stage == GAME_OVER:
                if ask_retry_battle():
                    revive_for_retry(player)
                    stage = BATTLE
                    savegame.save_game(player, stage)
                    return run_story(player, stage)
                return stage
    return stage

def revive_for_retry(player):
    player.health = 100
    player.mana = 100
    player.is_alive = True

def ask_retry_battle():
    while True:
        time.sleep(1)
        choice = input("Fight the dragon again? [y/n] ")
        if choice in ("y", "n"):
            return choice == "y"
        print("Enter y or n.")

def ask_quit_or_continue():
    return play_again_title()

def play_again_title():
    while True:
        time.sleep(1)
        choice = input("Return to title screen? [y/n] ")
        if choice == "y":
            return True
        elif choice == "n":
            return False
        else:
            print("Enter y or n.")

def play_again():
    while True:
        time.sleep(1)
        choice = input("Play again? [y/n] ")
        if choice == "y":
            return True
        elif choice == "n":
            return False
        else:
            input("Enter y or n. ")

if __name__ == "__main__":
    main()
