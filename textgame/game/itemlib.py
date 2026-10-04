

class Items(object):

    IDS = {
        1: 'wood',
        2: 'stone',
        3: 'dirt',
        4: 'gravel',
        5: 'water',
        6: 'wooden axe',
        7: 'wooden sword',
        8: 'stone axe',
        9: 'stone sword'
    }

    def __init__(self, item='item type', durability=0, gain=0,
        materials=0, id=0):
        self.item = item
        self.durability = durability
        self.gain = gain
        self.materials = materials
        self.id = id

    def item_id(self, id):
        return self.IDS.get(id)

    def all_items(self):
        for k, v in sorted(self.IDS.items()):
            print((v))
