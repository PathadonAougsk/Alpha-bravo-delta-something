"""The bag: the little panel that opens when ITEM is picked.

One row per thing you are carrying, with what is left of it on the right. The
row that is picked gets the same orange diamond the target cursor uses, so a
pick reads the same whether it is pointing at a HEAD or at a row in here. A
row with nothing left of it is dimmed, and picking it costs nothing.
"""

import pygame

from items import BLURBS, LABELS, ORDER

PANEL = (24, 30, 58)
EDGE = (90, 120, 210)
TEXT = (235, 238, 255)
DIM = (120, 128, 156)
BLURB = (170, 180, 210)
PICK = (255, 148, 38)      # the orange the target cursor is drawn in
PICK_ROW = (46, 58, 104)   # the band behind the row that is picked

WIDTH = 236
ROW_HEIGHT = 30
PAD = 10
MARKER = 7  # half-height of the little diamond in the margin


class ItemMenu:
    """Draws the bag. The pick itself lives on the battle, not in here."""

    def __init__(self):
        self._font = None
        self._small = None

    def size(self):
        return (WIDTH, PAD * 2 + ROW_HEIGHT * len(ORDER) + 18)

    def draw(self, surface, center, stock, index):
        """Lay the bag out around `center`, with row `index` picked."""
        if self._font is None:
            self._font = pygame.font.SysFont(None, 26, bold=True)
            self._small = pygame.font.SysFont(None, 19)

        panel = pygame.Rect((0, 0), self.size())
        panel.center = (round(center[0]), round(center[1]))
        pygame.draw.rect(surface, PANEL, panel)
        pygame.draw.rect(surface, EDGE, panel, 2)

        for i, name in enumerate(ORDER):
            left = stock.get(name, 0)
            row = pygame.Rect(
                panel.x + 2, panel.y + PAD + i * ROW_HEIGHT, panel.width - 4, ROW_HEIGHT
            )
            if i == index:
                pygame.draw.rect(surface, PICK_ROW, row)
                self._draw_marker(surface, (row.x + PAD + MARKER, row.centery))
            color = TEXT if left else DIM
            label = self._font.render(LABELS[name], True, color)
            count = self._font.render(f"x{left}", True, color)
            surface.blit(label, (row.x + PAD * 2 + MARKER * 2, row.centery - 9))
            surface.blit(count, (row.right - PAD - count.get_width(), row.centery - 9))

        # what the picked row actually does, along the bottom
        blurb = self._small.render(BLURBS[ORDER[index]], True, BLURB)
        surface.blit(blurb, (panel.x + PAD, panel.bottom - PAD - blurb.get_height()))

    def _draw_marker(self, surface, center):
        """The orange diamond in the margin of the picked row."""
        x, y = center
        pygame.draw.polygon(
            surface,
            PICK,
            [(x, y - MARKER), (x + MARKER, y), (x, y + MARKER), (x - MARKER, y)],
        )
