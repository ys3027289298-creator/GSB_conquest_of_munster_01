from Area import Area
from Item import Item


class Game:

    def __init__(self, start_area):
        if (start_area == None):
            raise ValueError("start_area should be given")

        self.__start_area = start_area
        self.__current_area = start_area
        self.__inventory = set()
        self.__events = {}
        self.__triggered_events = set()

    @property
    def startArea(self):
        return self.__start_area

    @property
    def currentArea(self):
        return self.__current_area

    @property
    def inventory(self):
        return self.__inventory

    def moveTo(self, area):
        target = self.__resolveArea(area)

        if (target not in self.__current_area.adjacents):
            raise ValueError("area '{0}' is not adjacent to '{1}'".format(target.name, self.__current_area.name))

        self.__current_area = target
        return target

    def __resolveArea(self, area):
        if (isinstance(area, Area)):
            return area

        if (isinstance(area, str)):
            if (area.strip().__len__() == 0):
                raise ValueError("area name should not be empty")

            for adjacent in self.__current_area.adjacents:
                if (adjacent.name == area):
                    return adjacent

            raise ValueError("no adjacent area named '{0}'".format(area))

        raise ValueError("area should be an Area or an area name")

    def take(self, item):
        if (item == None):
            raise ValueError("item should be given")

        if (not self.__current_area.removeItem(item)):
            return False

        self.__inventory.add(item)
        return True

    def drop(self, item):
        if (item == None):
            raise ValueError("item should be given")

        if (item not in self.__inventory):
            return False

        self.__inventory.discard(item)
        self.__current_area.addItem(item)
        return True

    def on(self, event_name, action):
        if (not isinstance(event_name, str) or event_name.strip().__len__() == 0):
            raise ValueError("event name should not be empty")

        if (not callable(action)):
            raise ValueError("event action should be callable")

        self.__events.setdefault(event_name, []).append(action)

    def trigger(self, event_name):
        if (not isinstance(event_name, str) or event_name.strip().__len__() == 0):
            raise ValueError("event name should not be empty")

        if (event_name in self.__triggered_events):
            return False

        self.__triggered_events.add(event_name)

        for action in self.__events.get(event_name, []):
            action(self, event_name)

        return True

    def hasTriggered(self, event_name):
        return event_name in self.__triggered_events

    def save(self):
        return {
            'current_area': self.__current_area.name,
            'inventory': [
                {'name': item.name, 'description': item.description}
                for item in self.__inventory
            ],
        }

    @classmethod
    def load(cls, save_data, areas):
        if (save_data == None):
            raise ValueError("save data should be given")

        if (not isinstance(save_data, dict)):
            raise ValueError("save data should be a dict")

        if ('current_area' not in save_data):
            raise ValueError("save data is missing 'current_area'")

        if ('inventory' not in save_data):
            raise ValueError("save data is missing 'inventory'")

        area_name = save_data['current_area']

        if (not isinstance(area_name, str) or area_name.strip().__len__() == 0):
            raise ValueError("current_area should not be empty")

        areas_by_name = {}
        for area in areas:
            areas_by_name[area.name] = area

        if (area_name not in areas_by_name):
            raise ValueError("unknown area '{0}'".format(area_name))

        game = cls(areas_by_name[area_name])

        saved_inventory = save_data['inventory']
        if (not isinstance(saved_inventory, list)):
            raise ValueError("inventory should be a list")

        for saved_item in saved_inventory:
            if (not isinstance(saved_item, dict)):
                raise ValueError("saved item should be a dict")

            if ('name' not in saved_item):
                raise ValueError("saved item is missing 'name'")

            item_name = saved_item['name']
            if (not isinstance(item_name, str) or item_name.strip().__len__() == 0):
                raise ValueError("item name should not be empty")

            game.__inventory.add(Item(item_name, saved_item.get('description')))

        return game
