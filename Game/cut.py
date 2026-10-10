"""The cut the battle opens and closes on.

Two screens part on it - the one the intro lifts off the fight and the one
the ending brings back down over the splash - and they part the same way, so
the geometry of it lives here rather than in either of them, the way the
glass does.

It is laid over at CUT rather than run flat across the screen, so what opens
and shuts is a diagonal and the corners go first and come back last. At
CUT = 0 everything in here collapses to the flat letterbox it started as:
`reach` comes out at half the height and the halves are two plain bars.
"""

import pygame

CUT = 45  # degrees the cut is laid at; 0 lays it flat across the screen
SEAM = 3  # the lit edge the halves part and meet on


def across(angle=CUT):
    """The way the cut runs, and the way the halves travel square to it."""
    along = pygame.Vector2(1, 0).rotate(angle)
    return along, along.rotate(-90)


def reach(size, angle=CUT):
    """How far the furthest corner sits, measured the way the halves travel.

    Further on a diagonal than on a flat edge, because the corners are
    further off one: at 45 degrees on an 800x600 screen it is 495 rather
    than the 300 a flat cut would need.
    """
    _, square = across(angle)
    width, height = size
    return abs(width / 2 * square.x) + abs(height / 2 * square.y)


def draw_halves(surface, size, apart, fill, seam=None, angle=CUT, width=SEAM):
    """The two halves, `apart` of the way off the screen along the cut.

    0 has them meeting in the middle with the screen shut behind them; 1 has
    them clear of it altogether. `seam` is the lit edge each one carries,
    drawn only while there is still screen on both sides of it to read it
    against.
    """
    if apart >= 1:
        return
    along, square = across(angle)
    out = reach(size, angle)
    gap = out * max(0.0, apart)
    middle = pygame.Vector2(size[0] / 2, size[1] / 2)
    run = (out + max(size)) * 2  # past the corners, whichever way it is laid

    for way in (square, -square):
        edge = middle + way * gap
        pygame.draw.polygon(
            surface,
            fill,
            [
                edge - along * run,
                edge + along * run,
                edge + along * run + way * run,
                edge - along * run + way * run,
            ],
        )
        if seam is not None and width < gap < out - width:
            pygame.draw.line(
                surface, seam, edge - along * run, edge + along * run, width
            )
