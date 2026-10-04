def _check_number(name, value, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError('%s must be a number, got %r' % (name, value))
    if not lo <= value <= hi:
        raise ValueError('%s must be between %s and %s, got %r'
                         % (name, lo, hi, value))
    return value


class Monster(object):

    MAX_LEVEL = 100
    MAX_HEIGHT = 1000
    MAX_ATTACK = 1000
    MAX_HP = 10000

    def __init__(self, name='monster', level=1, height=10, attack=1, hp=None):
        if not isinstance(name, str) or not name:
            raise ValueError('name must be a non-empty string')
        self.name = name
        self.level = _check_number('level', level, 1, self.MAX_LEVEL)
        self.height = _check_number('height', height, 0, self.MAX_HEIGHT)
        self.attack = _check_number('attack', attack, 0, self.MAX_ATTACK)
        if hp is None:
            hp = 10 * self.level
        self.hp = _check_number('hp', hp, 1, self.MAX_HP)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        _check_number('amount', amount, 0, self.MAX_HP)
        self.hp = max(0, self.hp - amount)
        return self.hp

    def describe(self):
        return '{name}, {level}, {height}, {attack}'.format(
            name=self.name, level=self.level,
            height=self.height, attack=self.attack)
