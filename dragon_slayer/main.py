from story.intro import intro
from story.training import training
from story.fishing import fishing
from story.battle import battle
from story.state import GameState, TRAINING, FISHING, BATTLE, LOST, WON
import time

STAGES = {
    TRAINING: training,
    FISHING: fishing,
    BATTLE: battle,
}

def main():
    playing = True
    while playing:
        state = load_or_intro()
        run_stages(state)
        playing = play_again()
    print("\nThanks for playing!\n")

def load_or_intro():
    if GameState.exists():
        state = GameState.load()
        if state.node != WON and ask_continue():
            return state
        GameState.clear()
    player = intro()
    return GameState.new_game(player)

def ask_continue():
    while True:
        time.sleep(1)
        choice = input("\nSave data found. Continue your saved game? [y/n] ")
        if choice == "y":
            return True
        elif choice == "n":
            return False
        print("Enter y or n.")

def run_stages(state):
    if state.node == LOST:
        state.advance()
    while state.node in STAGES:
        GameState(state.node, state.player).save()
        snapshot = GameState(state.node, state.player).to_dict()
        result = STAGES[state.node](state.player)
        if state.node == BATTLE and not result:
            lost_state = GameState.from_dict(snapshot)
            lost_state.node = LOST
            lost_state.save()
            return
        state.advance()
        GameState(state.node, state.player).save()
    if state.node == WON:
        GameState.clear()

def play_again():
    while True:
        time.sleep(1)
        choice = input("Play again? [y/n] ")
        if choice == "y":
            return True
        elif choice == "n":
            return False
        else:
            print("Enter y or n. ")

if __name__ == "__main__":
    main()
