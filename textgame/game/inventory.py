

class Inventory():

    DEFAULT_SLOTS = {
        'wood': 1,
        'stone': 0,
        'dirt': 0,
        'gravel': 0,
        'water': 0,
        'wooden axe': 0,
        'wooden sword': 0,
        'stone axe': 0,
        'stone sword': 0
    }

    def __init__(self):
        self.slots = dict(self.DEFAULT_SLOTS)

    def add(self, item, count=1):
        if item not in self.slots:
            raise KeyError(item)
        self.slots[item] += count
        return self.slots[item]

    def remove(self, item, count=1):
        if item not in self.slots:
            raise KeyError(item)
        self.slots[item] = max(0, self.slots[item] - count)
        return self.slots[item]

    def bag(self):
        for k, v in sorted(self.slots.items()):
            print((k, v))
        return ' '
