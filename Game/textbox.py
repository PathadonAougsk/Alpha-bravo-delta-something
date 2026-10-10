"""The text box: black, ruled in white, with a face in the margin.

What the game talks through when it has something to say that is worth
stopping for. The lines come up a letter at a time behind the asterisk
Undertale marks all its narration with, and a portrait sits in the left
margin so you can see who is doing the talking.

When the box is asking rather than saying, the choices run along the bottom
of it and the red soul sits in front of whichever one is picked - the same
soul the determination box is steered around, because it is the same soul.

The box knows nothing about the battle. It is handed lines, a face and a
list of choices, and it is handed the pick back when it draws; whose turn it
is and what the choices mean are the battle's business, not its own.
"""

import pygame

import assets

BACKDROP = (0, 0, 0)
BOX_LINE = (255, 255, 255)  # the box is one white rule on black, as it is in Undertale
TEXT = (255, 255, 255)
PICKED = (255, 255, 0)      # the yellow the option under the soul is lit in
SOUL = (255, 0, 0)

BOX_LINE_WIDTH = 5
PAD = 18           # inside the rule, before anything is drawn
LINE_HEIGHT = 30   # between one line of talk and the next
TEXT_SIZE = 27
PORTRAIT_GAP = 18  # between the face and the first letter of the talk

TYPING = 44.0      # letters a second, which is about the speed of being read to

OPTION_SIZE = 27
OPTION_GAP = 64    # between the end of one choice and the start of the next
SOUL_SIZE = 9      # half-height of the heart in front of the picked choice
SOUL_GAP = 28      # the margin it is given, in front of the word


def draw_soul(surface, spot, size=SOUL_SIZE, color=SOUL):
    """The heart: two lobes and a point, the way a soul is drawn."""
    x, y = spot
    pygame.draw.circle(surface, color, (x - size * 0.46, y - size * 0.3), size * 0.54)
    pygame.draw.circle(surface, color, (x + size * 0.46, y - size * 0.3), size * 0.54)
    pygame.draw.polygon(
        surface,
        color,
        [
            (x - size * 0.95, y - size * 0.18),
            (x + size * 0.95, y - size * 0.18),
            (x, y + size),
        ],
    )


class TextBox:
    """Draws what it was told to say. The pick itself lives on the caller."""

    def __init__(self):
        self.lines = ()
        self.options = ()
        self.portrait = None
        self.live = False
        self.shown = 0.0  # letters of the whole speech that have arrived so far

    # ------------------------------------------------------------- the talk

    def say(self, lines, portrait=None, options=()):
        """Open the box on `lines`, with `portrait` in the margin if there is one."""
        self.lines = tuple(lines)
        self.options = tuple(options)
        self.portrait = portrait  # an asset name, or None for no face
        self.live = True
        self.shown = 0.0

    def close(self):
        """The box has been answered; it is no longer anything's business."""
        self.live = False

    @property
    def letters(self):
        return sum(len(line) for line in self.lines)

    @property
    def typed(self):
        """True once the last letter is up - and only then are the choices live."""
        return self.shown >= self.letters

    def skip(self):
        """Land the rest of the speech at once, the way a key press does."""
        self.shown = self.letters

    def advance(self, dt):
        if self.live and not self.typed:
            self.shown = min(self.letters, self.shown + TYPING * dt)

    # ---------------------------------------------------------------- shape

    def face(self, size):
        """The portrait, cut to a square `size` across. None when missing.

        The sprite is scaled to the width of the margin and then cropped to
        the top of itself rather than fitted whole into it: what is worth
        looking at while somebody talks is their face, and on a sprite that
        stands up that is the top of it.
        """
        if self.portrait is None:
            return None
        image = assets.load(self.portrait)
        if image is None:
            return None
        tall = round(size * image.get_height() / image.get_width())
        scaled = assets.by_height(self.portrait, tall)
        square = pygame.Rect(0, 0, min(size, scaled.get_width()), min(size, scaled.get_height()))
        return scaled.subsurface(square)

    # -------------------------------------------------------------- drawing

    def draw(self, surface, rect, picked=0):
        """Lay the box out in `rect`, with choice `picked` under the soul."""
        rect = pygame.Rect(rect)
        pygame.draw.rect(surface, BACKDROP, rect)
        pygame.draw.rect(surface, BOX_LINE, rect, BOX_LINE_WIDTH)

        inside = rect.inflate(-(BOX_LINE_WIDTH + PAD) * 2, -(BOX_LINE_WIDTH + PAD) * 2)
        left = inside.left
        face = self.face(inside.height)
        if face is not None:
            surface.blit(face, face.get_rect(midleft=(inside.left, inside.centery)))
            left = inside.left + face.get_width() + PORTRAIT_GAP

        self.draw_lines(surface, left, inside.top)
        if self.options and self.typed:
            self.draw_options(surface, left, inside.bottom, picked)

    def draw_lines(self, surface, left, top):
        """The talk, as much of it as has arrived, a line under a line."""
        font = assets.font(TEXT_SIZE)
        shown = int(self.shown)
        for i, line in enumerate(self.lines):
            if shown <= 0:
                break  # the speech has not got this far down yet
            surface.blit(font.render(line[:shown], True, TEXT), (left, top + i * LINE_HEIGHT))
            shown -= len(line)

    def draw_options(self, surface, left, bottom, picked):
        """The choices in a row, with the soul in front of the one that is picked."""
        font = assets.font(OPTION_SIZE)
        x = left + SOUL_GAP  # the margin the soul needs in front of the first one
        y = bottom - font.get_height()
        for i, option in enumerate(self.options):
            text = font.render(option, True, PICKED if i == picked else TEXT)
            surface.blit(text, (x, y))
            if i == picked:
                draw_soul(surface, (x - SOUL_GAP * 0.6, y + text.get_height() / 2))
            x += text.get_width() + OPTION_GAP
