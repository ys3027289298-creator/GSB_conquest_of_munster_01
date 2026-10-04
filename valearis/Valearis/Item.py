class Item:

    def __init__(self, name, description = None):
        self.__name = name
        self.__description = description

    @property
    def name(self):
        return self.__name

    @property
    def description(self):
        return self.__description

    def __eq__(self, other):
        if not isinstance(other, Item):
            return NotImplemented
        return self.__name == other.__name and self.__description == other.__description

    def __hash__(self):
        return hash((self.__name, self.__description))
