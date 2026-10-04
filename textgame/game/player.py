from inventory import Inventory


class Player(object):

    def __init__(self, name='', max_health=100):
        self.name = name
        self.inv = Inventory()
        self.max_health = max_health
        self.health = max_health
        self.alive = True
        self.held = ' '

# Naming your player for a nice personal touch; when saving is implemented
# this will be saved as well.
    def player_name(self):
        if self.name == '':
            self.name = input('Would you like to give yourself a name?> ')
            print((self.name))
        else:
            print((('Your name is ' + repr(self.name))))

# The importance what hand you are holding will be important later on.
    def hand(self, right_hand=' \n', left_hand=' \n'):
        return self.held

    def right_hand(self, item=' '):
        self.held = item
        return self.held

    def take_damage(self, amount):
        if not self.alive:
            return 0
        self.health = max(0, self.health - amount)
        if self.health == 0:
            self.alive = False
        return self.health

    def heal(self, amount):
        if not self.alive:
            return 0
        self.health = min(self.max_health, self.health + amount)
        return self.health
