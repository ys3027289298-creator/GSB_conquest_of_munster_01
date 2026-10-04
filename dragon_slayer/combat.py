import time


def apply_damage(attacker, target, damage):
    """Apply damage to the target, clamping at the zero-health boundary."""
    if not getattr(attacker, "is_alive", True) or not target.is_alive:
        return
    damage = max(0, int(damage))
    dealt = min(target.health, damage)
    target.health -= dealt
    target.is_alive = target.health > 0
    return dealt
