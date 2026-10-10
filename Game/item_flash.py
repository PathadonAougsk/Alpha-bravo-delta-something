"""The wipe an item goes off in.

The field drops to black and a blue circle opens in the middle of it, growing
until there is nothing on the screen but blue - that is the whole of the item
being used, as far as the screen is concerned - and then the blue fades off
the battle that was underneath it all along. The retro filter is wound up
along with it, so the whole thing goes blocky and comes back into focus.
Nothing waits on it: the turn carries on behind it and the wipe is only ever
drawn over the top.
"""

import math

import pygame

BLUE = (72, 148, 255)  # the same blue the intro's cut-out comes in as
BACKDROP = (0, 0, 0)    # what the field is swapped for while the circle grows
EDGE = (190, 225, 255)  # a lighter rim on the circle, while it is still a circle

GROW = 0.26  # seconds the circle takes to swallow the screen
FADE = 0.38  # and seconds the blue takes to clear off the battle again
EDGE_WIDTH = 6
PIXELS = 14  # how chunky the retro filter is cranked to at the thick of it


def ease_out(progress):
    """0 to 1, quick off the mark and settling at the end."""
    return 1 - (1 - min(1.0, max(0.0, progress))) ** 3


class ItemFlash:
    """The wipe. Begin it, advance it every frame, draw it while it is live."""

    def __init__(self, width, height):
        self.size = (width, height)
        self.age = 0.0
        self.spot = (width / 2, height / 2)
        self.live = False

    # -------------------------------------------------------------- progress

    def begin(self, spot=None):
        """Open the circle at `spot`, or the middle of the screen without one."""
        self.spot = tuple(spot) if spot is not None else (
            self.size[0] / 2,
            self.size[1] / 2,
        )
        self.age = 0.0
        self.live = True

    def advance(self, dt):
        if not self.live:
            return
        self.age += dt
        if self.age >= GROW + FADE:
            self.live = False

    @property
    def reach(self):
        """Radius that puts the circle past the furthest corner of the screen."""
        width, height = self.size
        x, y = self.spot
        return max(
            math.hypot(x - corner_x, y - corner_y)
            for corner_x in (0, width)
            for corner_y in (0, height)
        )

    def crunch(self, base=1):
        """Pixels per pixel to present the frame at while the wipe runs.

        The wipe does not pixelate itself: it leans on the retro filter the
        whole game is already drawn through, winding it up to PIXELS as the
        circle grows and back down to `base` as the blue clears. So the heal
        blocks the screen up on the way in and the battle comes back into
        focus on the way out, HUD, text and all.
        """
        if not self.live:
            return base
        if self.age < GROW:
            climb = ease_out(self.age / GROW)
        else:
            climb = max(0.0, 1 - (self.age - GROW) / FADE)
        return max(base, round(base + (PIXELS - base) * climb))

    # --------------------------------------------------------------- drawing

    def draw(self, surface):
        """Lay the wipe over a finished frame."""
        if not self.live:
            return

        if self.age < GROW:
            # the field goes the moment the circle opens: there is nothing to
            # watch but the blue coming, on black
            surface.fill(BACKDROP)
            radius = self.reach * ease_out(self.age / GROW)
            pygame.draw.circle(surface, BLUE, self.spot, radius)
            # the rim only reads while there is still black outside the circle
            pygame.draw.circle(surface, EDGE, self.spot, radius, EDGE_WIDTH)
            return

        # full blue from here, thinning out until the battle is back
        left = 1 - (self.age - GROW) / FADE
        veil = pygame.Surface(self.size)
        veil.fill(BLUE)
        veil.set_alpha(round(255 * max(0.0, left)))
        surface.blit(veil, (0, 0))
