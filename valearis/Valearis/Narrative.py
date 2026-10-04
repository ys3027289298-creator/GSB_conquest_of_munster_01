__author__ = 'Michali'

class Narrative:

    def __init__(self, area):
        self.__intro = area.shortDescription
        self.__items = {item.description for item in area.items if item.description != None}
        self.__presentationOfItems = 'Here there are:' if self.__items.__len__() > 0 else None

    @property
    def intro(self):
        return self.__intro

    @property
    def presentationOfItems(self):
        return self.__presentationOfItems

    @property
    def items(self):
        return self.__items

class NarrativeNode:

    def __init__(self, text):
        if (text == None):
            raise ValueError("text should be given")

        self.__text = text
        self.__next_nodes = []

    @property
    def text(self):
        return self.__text

    @property
    def nextNodes(self):
        return tuple(self.__next_nodes)

    def addNext(self, node):
        if (node == None):
            raise ValueError("node should be given")

        if (node in self.__next_nodes):
            return False

        self.__next_nodes.append(node)
        return True

    def walk(self):
        order = []
        visiting = set()
        visited = set()

        def visit(node):
            if (node in visiting):
                raise ValueError("narrative nodes form a cycle")

            if (node in visited):
                return

            visiting.add(node)
            order.append(node)

            for next_node in node.__next_nodes:
                visit(next_node)

            visiting.discard(node)
            visited.add(node)

        visit(self)
        return order
