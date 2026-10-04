ITEM_IDS = {
    1: 'wood',
    2: 'stone',
    3: 'dirt',
    4: 'gravel',
    5: 'water',
    6: 'wooden axe',
    7: 'wooden sword',
    8: 'stone axe',
    9: 'stone sword',
}

ITEM_NAMES = tuple(ITEM_IDS.values())


class Items(object):

    def __init__(self, item='wood', durability=0, gain=0,
        materials=0, id=0):
        if item not in ITEM_NAMES:
            raise KeyError('unknown item: %r' % (item,))
        self.item = item
        self.durability = durability
        self.gain = gain
        self.materials = materials
        self.id = id

    @staticmethod
    def item_id(id):
        return ITEM_IDS.get(id)
