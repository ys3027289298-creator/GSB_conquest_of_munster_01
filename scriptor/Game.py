import Misc

class Game(object):
    def __init__(self, rooms, player, global_commands = None):

        self.rooms = rooms
        self.global_commands = global_commands if global_commands is not None else {}
        self.player = player
        self.validate()

    def validate(self):
        """Check the game state for authoring mistakes and report them
        as Misc.ScriptError instead of failing later with a crash."""
        if not any(self.player.loc is room for room in self.rooms.values()):
            raise Misc.ScriptError(
                "the player starts in room '%s', which is not one of the defined rooms: %s"
                % (getattr(self.player.loc, "ID", "?"), ", ".join(sorted(self.rooms.keys()))))
        for roomID, room in self.rooms.items():
            for direction, destination in room.connections.items():
                if destination not in self.rooms:
                    raise Misc.ScriptError(
                        "room '%s' has exit '%s' leading to undefined room '%s'"
                        % (roomID, direction, destination))
            seenIDs = set()
            for item in room.items:
                if item.ID in seenIDs:
                    raise Misc.ScriptError(
                        "room '%s' contains more than one item with ID '%s'"
                        % (roomID, item.ID))
                seenIDs.add(item.ID)

    def gameLoop(self):
        self.lastCommand = ""
        while True:
            self.player.loc.printDetails()

            self.lastCommand = input()

            if self.lastCommand == "!exit!":
                print("Game Ended")
                break

            self.handleCommand(self.lastCommand)

    def handleCommand(self, command):
        if command in self.player.loc.commands.keys():
            exec(self.player.loc.commands[command])
        elif command in self.player.loc.connections.keys():
            destination = self.player.loc.connections[command]
            if destination in self.rooms:
                self.player.goto(self.rooms[destination])
            else:
                print("You can't go that way. (room '%s' is not defined)" % destination)
        elif command in self.global_commands.keys():
            if "!x!" in self.global_commands[command]:
                print("'%s' needs something to act on (e.g. '%s bar')" % (command, command))
            else:
                exec(self.global_commands[command])
        elif command.split(' ', 1)[0] in self.global_commands.keys():
            exec(self.global_commands[command.split(' ', 1)[0]].replace("!x!", command.split(' ', 1)[1]))
        else:
            print("Sorry, I don't understand what you mean")
