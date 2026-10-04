class NarrativeLoopError(Exception):
    pass


class NarrativeNode:

    def __init__(self, name, text=None):
        if name is None or name == '':
            raise ValueError("name should be given")
        self.__name = name
        self.__text = text
        self.__next = {}

    @property
    def name(self):
        return self.__name

    @property
    def text(self):
        return self.__text

    def addChoice(self, label, node):
        if label is None or label == '':
            raise ValueError("label should be given")
        if node is None:
            raise ValueError("node should be given")
        self.__next[label] = node
        return node

    @property
    def choices(self):
        return dict(self.__next)

    def choice(self, label):
        try:
            return self.__next[label]
        except KeyError:
            raise KeyError("unknown choice '%s' at node '%s'" % (label, self.__name))


class Story:

    def __init__(self, start):
        if start is None:
            raise ValueError("start node should be given")
        self.__start = start
        self.__current = start
        self.__visited = {id(start)}

    @property
    def start(self):
        return self.__start

    @property
    def current(self):
        return self.__current

    def choose(self, label):
        node = self.__current.choice(label)
        if id(node) in self.__visited:
            raise NarrativeLoopError(
                "narrative loop detected at node '%s'" % node.name)
        self.__visited.add(id(node))
        self.__current = node
        return node

    def walk(self, labels):
        for label in labels:
            self.choose(label)
        return self.__current

    def reset(self):
        self.__current = self.__start
        self.__visited = {id(self.__start)}

    def to_dict(self):
        return {'current': self.__current.name}

    def loadState(self, data):
        if not isinstance(data, dict) or 'current' not in data:
            raise ValueError("missing field 'current'")
        target = data['current']
        visited = set()
        stack = [self.__start]
        while stack:
            node = stack.pop()
            if id(node) in visited:
                continue
            visited.add(id(node))
            if node.name == target:
                self.__current = node
                return
            stack.extend(node.choices.values())
        raise KeyError("unknown node '%s'" % target)
