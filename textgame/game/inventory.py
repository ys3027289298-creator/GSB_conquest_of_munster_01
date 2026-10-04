from itemlib import ITEM_NAMES


class Inventory():
    def __init__(self):
        self.slots = {name: 0 for name in ITEM_NAMES}

    def add_item(self, item, count=1):
        if item not in self.slots:
            raise KeyError('unknown item: %r' % (item,))
        if count < 1:
            raise ValueError('count must be >= 1')
        self.slots[item] += count
        return self.slots[item]

    def has_item(self, item):
        return self.slots.get(item, 0) > 0

    def take_item(self, item, count=1):
        if not self.has_item(item):
            raise KeyError('item not in inventory: %r' % (item,))
        if count > self.slots[item]:
            raise ValueError('not enough %r in inventory' % (item,))
        self.slots[item] -= count
        return self.slots[item]

    def bag(self):
        for k, v in sorted(self.slots.items()):
            print((k, v))
        return ' '
