"""The run-up to the battle.

The screen opens black and splits across the middle: the two halves part on a
lit seam to reveal the player behind them, a flat blue cut-out standing the
full height of the screen. It shrinks back to its own size as it travels to
the spot it fights from, and the moment it lands the colour washes in and the
battle is on.
"""

import pygame

import assets
from player import SPRITE_HEIGHT

FIGURE = (72, 148, 255)  # the blue the cut-out comes in as
BACKDROP = (0, 0, 0)

SPLIT = 0.32   # seconds the two black halves take to part
HOLD = 0.12    # beat with the cut-out standing there at full height
TRAVEL = 0.56  # seconds it takes to reach the spot it fights from
WASH = 0.3     # seconds the colour takes to come back once it lands
FILL = 1.0     # how much of the screen the cut-out covers to start: 1 fills it
SEAM = 3       # the lit edge each half parts on


def ease_out(progress):
    """0 to 1, quick off the mark and settling at the end."""
    return 1 - (1 - min(1.0, max(0.0, progress))) ** 3


class Intro:
    """The opening sweep. Advance it every frame and draw it while it runs."""

    def __init__(self, width, height):
        self.size = (width, height)
        self.age = 0.0
        self._cutout = None

    # -------------------------------------------------------------- progress

    def advance(self, dt):
        self.age += dt

    def skip(self):
        """Drop straight into the fight."""
        self.age = self.total

    @property
    def total(self):
        return SPLIT + HOLD + TRAVEL + WASH

    @property
    def running(self):
        return self.age < self.total

    @property
    def covering(self):
        """True while the intro owns the whole screen, colour and all."""
        return self.age < SPLIT + HOLD + TRAVEL

    @property
    def parted(self):
        """0 with the halves shut, 1 once they are clear of the screen."""
        return ease_out(self.age / SPLIT)

    @property
    def veil(self):
        """1 the moment the cut-out lands, 0 once the colour is all the way back."""
        if self.covering:
            return 1.0
        return max(0.0, 1 - (self.age - SPLIT - HOLD - TRAVEL) / WASH)

    # --------------------------------------------------------------- drawing

    def cutout(self):
        """The player's outline, filled flat blue. Built once."""
        if self._cutout is None:
            sprite = assets.by_height(assets.PLAYER, SPRITE_HEIGHT)
            if sprite is None:
                return None
            # the mask is the sprite's own shape, so the silhouette is exact
            shape = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
            pygame.mask.from_surface(sprite).to_surface(
                shape, setcolor=FIGURE, unsetcolor=(0, 0, 0, 0)
            )
            self._cutout = shape
        return self._cutout

    def draw(self, surface, player):
        """Black out the screen and place the cut-out, or veil what is already drawn.

        While `covering` this owns the frame. Afterwards the caller draws the
        battle as usual and this lays the fading black over the top, so the
        colour comes up underneath a cut-out that is already in position.
        """
        landed = ease_out((self.age - SPLIT - HOLD) / TRAVEL)
        figure = self.cutout()

        if figure is not None:
            # it starts covering the screen outright - the sprite is tall and
            # narrow, so filling the width is what decides the scale - and
            # pulls back from there to its own height
            opening = FILL * max(
                self.size[0] / figure.get_width(), self.size[1] / figure.get_height()
            )
            zoom = opening + (1 - opening) * landed
            figure = pygame.transform.scale(
                figure,
                (round(figure.get_width() * zoom), round(figure.get_height() * zoom)),
            )
            # from the middle of the screen to where the player stands, which
            # is the same placement Player.draw uses, so the swap is seamless
            middle = pygame.Vector2(
                self.size[0] / 2, self.size[1] / 2 + figure.get_height() / 2
            )
            mark = pygame.Vector2(player.pos.x, player.pos.y + player.radius)
            feet = middle.lerp(mark, landed)

        if self.covering:
            surface.fill(BACKDROP)
            if figure is not None:
                surface.blit(figure, figure.get_rect(midbottom=feet))
            if self.age < SPLIT:
                self.draw_halves(surface)
            return

        veil = pygame.Surface(self.size)
        veil.fill(BACKDROP)
        if figure is not None:
            veil.blit(figure, figure.get_rect(midbottom=feet))
        veil.set_alpha(round(255 * self.veil))
        surface.blit(veil, (0, 0))

    def draw_halves(self, surface):
        """The two black halves, parting from the middle on a lit seam."""
        width, height = self.size
        half = height / 2
        shift = half * self.parted
        pygame.draw.rect(surface, BACKDROP, (0, -shift, width, half))
        pygame.draw.rect(surface, BACKDROP, (0, half + shift, width, half))
        if shift > 0:  # the lit edge, until the halves are gone
            pygame.draw.rect(surface, FIGURE, (0, half - shift - SEAM, width, SEAM))
            pygame.draw.rect(surface, FIGURE, (0, half + shift, width, SEAM))
