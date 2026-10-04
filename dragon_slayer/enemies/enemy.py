import time
from combat import apply_damage

class Enemy:
    def __init__(self, name):
        self.health = 100
        self.name = name
        self.is_alive = self.health > 0

    def use_ability(self, ability, target):
        if not self.is_alive or not target.is_alive:
            return
        time.sleep(1)
        print(f"{self.name} uses {ability} on you.")
        damage = self._calc_damage(ability)
        time.sleep(1)
        before = target.health
        apply_damage(self, target, damage)
        dealt = before - target.health
        print(f"You take {dealt} damage and have {target.health} health remaining.\n")
    
    def _calc_damage(self, ability):
        damage = max(0, int(10 * self.abilities[ability]["damage multiplier"]))
        return damage
