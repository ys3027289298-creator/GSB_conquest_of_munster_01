from inventory import Inventory


class Player(object):

	MAX_HP = 100

	def __init__(self, name=''):
		self.name = name
		self.inv = Inventory()
		self.hp = self.MAX_HP
		self.right_hand = None
		self.left_hand = None

	#Naming your player for a nice personal toouch, when saving is implemented
	#this will be save as well.
	def player_name(self):
		if self.name == '':
			self.name = input('Would you like to give yourself a name?> ')
			print((self.name))
		else:
			print((('Your name is ' + repr(self.name))))

	#The importance what hand you are will be important later on.

	def hand(self):
		if self.right_hand is None and self.left_hand is None:
			return ' '
		held = [item for item in (self.right_hand, self.left_hand) if item]
		return ' \n'.join(held)

	def hold(self, item, hand='right'):
		if hand == 'right':
			self.right_hand = item
		elif hand == 'left':
			self.left_hand = item
		else:
			raise ValueError('hand must be "right" or "left"')

	def is_alive(self):
		return self.hp > 0

	def take_damage(self, amount):
		if amount < 0:
			raise ValueError('damage must be >= 0')
		self.hp = max(0, self.hp - amount)
		return self.hp

	def heal(self, amount):
		if amount < 0:
			raise ValueError('heal must be >= 0')
		self.hp = min(self.MAX_HP, self.hp + amount)
		return self.hp
