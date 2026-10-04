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
        return self.name == other.name and self.description == other.description

    def __hash__(self):
        return hash((self.name, self.description))
