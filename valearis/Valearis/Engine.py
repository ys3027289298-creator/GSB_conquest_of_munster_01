import json

from Area import Area
from Item import Item
from Narrative import Narrative


class GameError(Exception):
    pass


class UnknownAreaError(GameError):
    pass


class AreaNotAdjacentError(GameError):
    pass


class ItemNotFoundError(GameError):
    pass


class DuplicateItemError(GameError):
    pass


class UnknownEventError(GameError):
    pass


class EventAlreadyFiredError(GameError):
    pass


class EmptyInputError(GameError, ValueError):
    pass


class UnknownCommandError(GameError):
    pass


class Event:

    def __init__(self, name, action=None):
        if name is None or name == '':
            raise ValueError("name should be given")
        self.__name = name
        self.__action = action if action is not None else (lambda game: None)
        self.__fired = False

    @property
    def name(self):
        return self.__name

    @property
    def fired(self):
        return self.__fired

    def fire(self, game):
        if self.__fired:
            raise EventAlreadyFiredError("event '%s' already fired" % self.__name)
        self.__fired = True
        return self.__action(game)

    def markFired(self):
        self.__fired = True


class Game:

    def __init__(self):
        self.__areas = {}
        self.__current = None
        self.__inventory = {}
        self.__events = {}
        self.__story = None
        self.__pendingStoryState = None

    def addArea(self, area):
        if area is None:
            raise ValueError("area should be given")
        if area.name in self.__areas:
            raise GameError("area '%s' already registered" % area.name)
        self.__areas[area.name] = area
        if self.__current is None:
            self.__current = area
        return area

    def area(self, name):
        try:
            return self.__areas[name]
        except KeyError:
            raise UnknownAreaError("unknown area '%s'" % name)

    @property
    def areas(self):
        return dict(self.__areas)

    @property
    def currentArea(self):
        return self.__current

    def startAt(self, area_name):
        self.__current = self.area(area_name)

    def move(self, area_name):
        target = self.area(area_name)
        if self.__current is not None and target not in self.__current.adjacents:
            raise AreaNotAdjacentError(
                "cannot move from '%s' to '%s'" % (self.__current.name, area_name))
        self.__current = target
        return Narrative(target)

    def take(self, item_name):
        if self.__current is None:
            raise GameError("no current area")
        for item in list(self.__current.items):
            if item.name == item_name:
                self.__current.items.discard(item)
                self.__inventory[item.name] = item
                return item
        raise ItemNotFoundError("no item '%s' here" % item_name)

    def drop(self, item_name):
        if self.__current is None:
            raise GameError("no current area")
        try:
            item = self.__inventory.pop(item_name)
        except KeyError:
            raise ItemNotFoundError("no item '%s' in inventory" % item_name)
        if any(existing.name == item.name for existing in self.__current.items):
            self.__inventory[item.name] = item
            raise DuplicateItemError(
                "an item named '%s' is already here" % item.name)
        self.__current.items.add(item)
        return item

    @property
    def inventory(self):
        return dict(self.__inventory)

    def addEvent(self, event):
        if event is None:
            raise ValueError("event should be given")
        self.__events[event.name] = event
        return event

    def triggerEvent(self, event_name):
        try:
            event = self.__events[event_name]
        except KeyError:
            raise UnknownEventError("unknown event '%s'" % event_name)
        return event.fire(self)

    def eventFired(self, event_name):
        try:
            return self.__events[event_name].fired
        except KeyError:
            raise UnknownEventError("unknown event '%s'" % event_name)

    def attachStory(self, story):
        self.__story = story
        if self.__pendingStoryState is not None:
            story.loadState(self.__pendingStoryState)
            self.__pendingStoryState = None
        return story

    @property
    def story(self):
        return self.__story

    def handle(self, raw_input):
        if raw_input is None:
            raise EmptyInputError("empty input")
        tokens = raw_input.split()
        if len(tokens) == 0:
            raise EmptyInputError("empty input")
        command = tokens[0].lower()
        argument = ' '.join(tokens[1:])
        if command == 'go':
            if argument == '':
                raise EmptyInputError("go where?")
            return self.move(argument)
        if command == 'take':
            if argument == '':
                raise EmptyInputError("take what?")
            return self.take(argument)
        if command == 'drop':
            if argument == '':
                raise EmptyInputError("drop what?")
            return self.drop(argument)
        if command == 'look':
            if self.__current is None:
                raise GameError("no current area")
            return Narrative(self.__current)
        if command == 'inventory':
            return sorted(self.__inventory)
        raise UnknownCommandError("unknown command '%s'" % command)

    def to_dict(self):
        areas = {}
        for name, area in self.__areas.items():
            areas[name] = {
                'short_description': area.shortDescription,
                'long_description': area.longDescription,
                'items': [
                    {'name': item.name, 'description': item.description}
                    for item in sorted(area.items, key=lambda item: str(item.name))
                ],
                'adjacents': sorted(adjacent.name for adjacent in area.adjacents),
            }
        return {
            'current_area': self.__current.name if self.__current is not None else None,
            'areas': areas,
            'inventory': [
                {'name': item.name, 'description': item.description}
                for item in sorted(self.__inventory.values(), key=lambda item: str(item.name))
            ],
            'fired_events': sorted(name for name, event in self.__events.items() if event.fired),
            'story': self.__story.to_dict() if self.__story is not None else None,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("save data should be a dict")
        for field in ('current_area', 'areas', 'inventory', 'fired_events'):
            if field not in data:
                raise ValueError("missing field '%s'" % field)
        game = cls()
        for name, area_data in data['areas'].items():
            for field in ('short_description', 'items', 'adjacents'):
                if field not in area_data:
                    raise ValueError("missing field '%s' for area '%s'" % (field, name))
            area = Area(name, area_data['short_description'], area_data.get('long_description'))
            for item_data in area_data['items']:
                if 'name' not in item_data:
                    raise ValueError("missing field 'name' for an item in area '%s'" % name)
                area.items.add(Item(item_data['name'], item_data.get('description')))
            game.addArea(area)
        for name, area_data in data['areas'].items():
            for adjacent_name in area_data['adjacents']:
                if adjacent_name not in game.__areas:
                    raise UnknownAreaError("unknown area '%s'" % adjacent_name)
                game.__areas[name].addAdjacent(game.__areas[adjacent_name])
        if data['current_area'] is not None:
            game.startAt(data['current_area'])
        else:
            game.__current = None
        for item_data in data['inventory']:
            if 'name' not in item_data:
                raise ValueError("missing field 'name' for an inventory item")
            item = Item(item_data['name'], item_data.get('description'))
            game.__inventory[item.name] = item
        for event_name in data['fired_events']:
            if event_name not in game.__events:
                game.addEvent(Event(event_name))
            game.__events[event_name].markFired()
        game.__pendingStoryState = data.get('story')
        return game

    def save(self, path):
        with open(path, 'w') as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path):
        with open(path) as fh:
            return cls.from_dict(json.load(fh))
