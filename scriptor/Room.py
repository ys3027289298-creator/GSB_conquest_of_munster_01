import Misc
import Parser

class Room(object):
    def __init__(self, ID, name = "default room", desc = "a normal looking room",
                 items = None, commands = None, connections = None, variables = None):
        self.ID = ID
        self.name = name
        self.desc = desc
        self.items = [] if items is None else items
        self.connections = {} if connections is None else connections
        self.commands = {} if commands is None else commands
        self.variables = {} if variables is None else variables

    def contains(self, itemName):
        if itemName in Misc.flatten([item.names for item in self.items]):
            return True
        else:
            return False

    def printDetails(self, player = None):
        print('\nRoom: ' + self.name)


        pDesc = Parser.desc_block.parseString(self.desc)
        # print(pDesc)
        print("Description:", end=" ")

        for token in pDesc[0]:
            if isinstance(token, str):
                print(token, end=" ")
            else:
                condition = token["if_condition"]
                if condition["verb"] == "has":
                    if player is not None:
                        held = [item.ID for item in player.inv]
                    else:
                        held = [item.ID for item in self.items]
                    if condition["object"] in held:
                        print(condition["condition_text"], end = " ")
                    elif "condition_text" in token["else_condition"]:
                        print(token["else_condition"]["condition_text"], end = " ")
                # if item[0] == "without":
                #     if item[1] in [item.ID for item in self.items]:
                #         print(item[2], end = " ")
                # print(item[2], end = " ")
        print()

        # print(pDesc)

        # print('Description: ' + self.desc + '\n')
