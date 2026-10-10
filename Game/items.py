"""What is in the bag.

Two things, and they are not alike: HEALTH keeps you standing, GUN takes you
off the board on purpose. There is one gun and using it ends the battle there
and then, after the cut-in that goes with it.
"""

HEALTH = "health"
GUN = "gun"

ORDER = (HEALTH, GUN)  # the order they are listed in, top to bottom

GUN_STOCK = 1  # the health stock is whatever the battle was started with

LABELS = {HEALTH: "HEALTH", GUN: "GUN"}
BLURBS = {
    HEALTH: "Patch yourself up.",
    GUN: "One shot. Ends it.",
}
