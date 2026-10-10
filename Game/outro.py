"""The splash the battle ends on.

The fight resolves into a comic-book finisher: the screen washes out, a burst
of spokes sweeps in behind, and the player lands across it huge and flipped,
facing back the way he came, with the result stamped over the top.
"""

import math

import pygame

import assets

FLASH = 0.14      # seconds of white-out the splash opens on
FIGURE_IN = 0.42  # seconds the figure takes to land
BANNER_IN = 0.34  # seconds the stamp takes, once the figure is down
BANNER_WAIT = 0.3  # and how long after the figure it waits

SPOKES = 18          # how many wedges in the burst
SPOKE_FILL = 0.44    # how much of its slice each wedge covers
SPIN = 0.35          # radians a second the burst turns
FOCUS = (0.63, 0.46)  # where the burst radiates from, as a fraction of the screen

FIGURE_HEIGHT = 1.26  # figure height as a multiple of the screen: it crops
FIGURE_FEET = (0.44, 1.16)  # where the figure's feet sit, likewise
FIGURE_SWEEP = 300    # pixels it travels on the way in
FIGURE_ZOOM = 0.22    # how much smaller it starts before settling

# victory reads cold and bright, defeat warm and dim
VICTORY = {
    "wash": (26, 34, 92),
    "spoke": (64, 116, 240),
    "glow": (120, 170, 255),
    "text": (255, 236, 140),
    "word": "VICTORY",
    "tilt": -7,
}
DEFEAT = {
    "wash": (40, 15, 22),
    "spoke": (104, 32, 46),
    "glow": (150, 60, 70),
    "text": (236, 206, 206),
    "word": "DEFEAT",
    "tilt": 4,
}


def ease_out(progress):
    """0 to 1, quick off the mark and settling at the end."""
    return 1 - (1 - min(1.0, max(0.0, progress))) ** 3


class Outro:
    """Draws the end-of-battle splash. Hand it the age of the result in seconds."""

    def __init__(self, width, height):
        self.size = (width, height)
        self._font = None
        self._figure = None

    # ------------------------------------------------------------------ parts

    def figure(self):
        """The player sprite, big and flipped, built once."""
        if self._figure is None:
            sprite = assets.by_height(assets.PLAYER, round(self.size[1] * FIGURE_HEIGHT))
            if sprite is None:
                return None
            # flipped, so he faces back across the field he just cleared
            self._figure = pygame.transform.flip(sprite, True, False)
        return self._figure

    def burst(self, look, turn):
        """The wedge burst behind the figure."""
        width, height = self.size
        surface = pygame.Surface(self.size, pygame.SRCALPHA)
        focus = pygame.Vector2(width * FOCUS[0], height * FOCUS[1])
        reach = max(self.size) * 1.6
        slice_ = math.tau / SPOKES
        for i in range(SPOKES):
            start = turn + i * slice_
            end = start + slice_ * SPOKE_FILL
            colour = look["spoke"] if i % 2 else look["glow"]
            pygame.draw.polygon(
                surface,
                (*colour, 150 if i % 2 else 90),
                [
                    focus,
                    focus + pygame.Vector2(math.cos(start), math.sin(start)) * reach,
                    focus + pygame.Vector2(math.cos(end), math.sin(end)) * reach,
                ],
            )
        return surface

    def stamp(self, look, landed):
        """The result word, tilted and popped in over everything else."""
        if self._font is None:
            self._font = pygame.font.SysFont(None, 128, bold=True, italic=True)
        word = self._font.render(look["word"], True, look["text"])
        edge = self._font.render(look["word"], True, (14, 12, 22))

        plate = pygame.Surface(
            (word.get_width() + 12, word.get_height() + 12), pygame.SRCALPHA
        )
        for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-4, -4), (4, 4)):
            plate.blit(edge, (6 + dx, 6 + dy))
        plate.blit(word, (6, 6))
        # overshoot a little, then settle back
        scale = 0.6 + 0.46 * landed - 0.06 * landed ** 2
        return pygame.transform.rotozoom(plate, look["tilt"], scale)

    # ----------------------------------------------------------------- drawing

    def draw(self, surface, won, age):
        """Paint the whole splash over `surface` for a result `age` seconds old."""
        look = VICTORY if won else DEFEAT
        width, height = self.size

        surface.fill(look["wash"])
        surface.blit(self.burst(look, age * SPIN), (0, 0))

        landed = ease_out(age / FIGURE_IN)
        figure = self.figure()
        if figure is not None:
            zoom = 1 - FIGURE_ZOOM * (1 - landed)
            grown = pygame.transform.scale(
                figure,
                (round(figure.get_width() * zoom), round(figure.get_height() * zoom)),
            )
            feet = (
                width * FIGURE_FEET[0] + FIGURE_SWEEP * (1 - landed),
                height * FIGURE_FEET[1],
            )
            surface.blit(grown, grown.get_rect(midbottom=feet))

        stamped = ease_out((age - FIGURE_IN - BANNER_WAIT) / BANNER_IN)
        if stamped > 0:
            word = self.stamp(look, stamped)
            word.set_alpha(round(255 * stamped))
            surface.blit(word, word.get_rect(center=(width * 0.52, height * 0.52)))

        # the whole thing opens on a white-out that burns off fast
        if age < FLASH:
            glare = pygame.Surface(self.size)
            glare.fill((255, 255, 255))
            glare.set_alpha(round(255 * (1 - age / FLASH)))
            surface.blit(glare, (0, 0))
