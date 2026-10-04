import copy

import Misc
from Misc import ScriptError

class Game(object):
    def __init__(self, rooms, player, global_commands = None):

        self.rooms = rooms
        self.global_commands = {} if global_commands is None else global_commands
        self.player = player
        self._validate()
        self._initial_state = copy.deepcopy((self.rooms, self.player))

    def _validate(self):
        if not any(room is self.player.loc for room in self.rooms.values()):
            raise ScriptError("player starts in a room that is not part of the game")
        for room in self.rooms.values():
            for keyword, destination in room.connections.items():
                if destination not in self.rooms:
                    raise ScriptError(
                        "room '{}' path '{}' leads to undefined room '{}'".format(room.ID, keyword, destination)
                    )
        seen = {}
        for holder in list(self.rooms.values()) + [self.player]:
            items = holder.inv if holder is self.player else holder.items
            for item in items:
                if not item.ID:
                    continue
                if item.ID in seen:
                    raise ScriptError("duplicate item id '{}'".format(item.ID))
                seen[item.ID] = True

    def restart(self):
        self.rooms, self.player = copy.deepcopy(self._initial_state)

    def gameLoop(self):
        self.lastCommand = ""
        while True:
            self.player.loc.printDetails(self.player)

            self.lastCommand = input()

            if self.lastCommand == "!exit!":
                print("Game Ended")
                break

            if self.lastCommand in self.player.loc.commands.keys():
                exec(self.player.loc.commands[self.lastCommand])
            elif self.lastCommand in self.player.loc.connections.keys():
                destination = self.player.loc.connections[self.lastCommand]
                if destination in self.rooms:
                    self.player.goto(self.rooms[destination])
                else:
                    print("You can't go that way")
            elif self.lastCommand in self.global_commands.keys():
                exec(self.global_commands[self.lastCommand])
            elif self.lastCommand.split(' ', 1)[0] in self.global_commands.keys():
                exec(self.global_commands[self.lastCommand.split(' ', 1)[0]].replace("!x!", self.lastCommand.split(' ', 1)[1]))

            else:
                print("Sorry, I don't understand what you mean")
