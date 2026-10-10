"""Every stat in the game is derived from one baseline number.

Each role is a set of multiples of the baseline, and each stat is rolled
with a little random spread so no two fighters come out identical.
"""

import random

BASE = 50
SPREAD = 0.15  # stats land within +/-15% of their baseline value

# multiples of the baseline, per role
PLAYER = {"health": 2.4, "mana": 1.6, "attack_damage": 0.5}
ENEMY = {"health": 0.8, "mana": 0.2, "attack_damage": 0.16}

ITEM_HEAL = 0.6  # an item restores 60% of the baseline


def vary(value, spread=SPREAD):
    """Nudge a number up or down by up to `spread`, never below 1."""
    return max(1, round(value * random.uniform(1 - spread, 1 + spread)))


def roll(profile, base=BASE, spread=SPREAD):
    """Roll a stat dict for a role profile around the baseline."""
    return {name: vary(base * mult, spread) for name, mult in profile.items()}
