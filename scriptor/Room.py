import Misc
import Parser

class Room(object):
    def __init__(self, ID, name = "default room", desc = "a normal looking room",
                 items = None, commands = None, connections = None,
                 script_commands = None, variables = None):
        self.ID = ID
        self.name = name
        self.desc = desc
        self.items = items if items is not None else []
        self.connections = connections if connections is not None else {}
        self.commands = commands if commands is not None else {}
        self.script_commands = script_commands if script_commands is not None else {}
        self.variables = variables if variables is not None else {}

    def contains(self, itemName):
        if itemName in Misc.flatten([item.names for item in self.items]):
            return True
        else:
            return False

    def printDetails(self):
        print('\nRoom: ' + self.name)


        if isinstance(self.desc, str):
            pDesc = Parser.desc_block.parseString(self.desc)[0]
        else:
            # Loader passes the already-parsed description blocks.
            pDesc = self.desc
        # print(pDesc)
        print("Description:", end=" ")

        for item in pDesc:
            if type(item) is str:
                print(item, end=" ")
            else:
                if item["if_condition"]["verb"] == "has":
                    condition = item["if_condition"]
                    objectID = condition["object"] if "object" in condition else None
                    if objectID not in [item.ID for item in self.items]:
                        print(condition["condition_text"], end = " ")
                    elif "else_condition" in item and "condition_text" in item["else_condition"]:
                        print(item["else_condition"]["condition_text"], end = " ")
                # if item[0] == "without":
                #     if item[1] in [item.ID for item in self.items]:
                #         print(item[2], end = " ")
                # print(item[2], end = " ")
        print()

        # print(pDesc)

        # print('Description: ' + self.desc + '\n')
