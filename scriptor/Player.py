import Misc
from Misc import ScriptError
from Room import Room

class Player(object):
    def __init__(self, room, inv = None):
        self.loc = room
        self.inv = [] if inv is None else inv

    def printInv(self):
        print("\n==========Inventory==========")
        for item in self.inv:
            print("| " + item.names[0] + " "*(26 - len(item.names[0])) + "|")
        print("=============================")

    def goto(self, room):
        if not isinstance(room, Room):
            raise ScriptError("player cannot move to undefined room {!r}".format(room))
        self.loc = room

    def addToInv(self, itemName):
        item = Misc.find(itemName, self.loc.items)
        self.inv.append(item)
        self.loc.items.remove(item)
        if item.takeDesc != "":
            print(item.takeDesc)
