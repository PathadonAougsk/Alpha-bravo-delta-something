"""The way the battle ends, win or lose.

It is built the way the gun's cut-in is: the last frame of the fight is
caught and held, the blow blows it out and kicks the lens, cracks run out
across it from the middle, and then the whole thing comes apart into panes
that turn over as they fall - except that what is underneath this time is
not nothing. The splash is already standing behind the glass: a burst of
spokes, the player landing across it huge and flipped, and the result
stamped over the top.

The last beat is the intro's, run backwards. The battle opened on two black
halves parting on a lit seam; it closes on them coming back in to letterbox
the splash, and a defeat keeps going until they have shut the screen.
"""

import math
import random

import pygame

import assets
import cut
import glass

# the beats, in order, in seconds
HIT = 0.18     # the blow lands: the frame is blown out and kicked
CRACK = 0.30   # cracks run out from the middle of the held frame
BREAK = 0.85   # and it falls away in panes, off the splash behind it
HOLD = 1.70    # which the splash is left standing for

# the splash itself, timed from the moment the glass starts to go
FIGURE_IN = 0.42   # seconds the figure takes to land
BANNER_WAIT = 0.3  # how long after the figure the stamp waits
BANNER_IN = 0.34   # and how long it takes once it comes

SPOKES = 18          # how many wedges in the burst
SPOKE_FILL = 0.44    # how much of its slice each wedge covers
SPIN = 0.35          # radians a second the burst turns
FOCUS = (0.63, 0.46)  # where the burst radiates from, as a fraction of the screen

FIGURE_HEIGHT = 1.26  # figure height as a multiple of the screen: it crops
FIGURE_FEET = (0.44, 1.16)  # where the figure's feet sit, likewise
FIGURE_SWEEP = 300    # pixels it travels on the way in
FIGURE_ZOOM = 0.22    # how much smaller it starts before settling

KICK = 26      # pixels the whole frame is thrown about as the blow lands
PUNCH = 0.11   # and how far it is shoved into the lens with it
SETTLE = 0.30  # seconds that kick takes to fall away

PANES = 17      # how many panes the held frame comes apart into
STAGGER = 0.45  # how far a pane's edge wanders off an even slice, 0 to 1
FALL = 1050     # pixels a pane travels out of the frame
DROP = 820      # and how far gravity drags it down on the way
PANE_SPIN = 130  # degrees it turns as it goes
PANE_FADE = 0.7  # the fraction of the fall it flies for before fading out
CRACKS = 20      # lines running out from the middle
CRACK_SEED = 2291
CRACK_KINKS = 6
CRACK_WIDTH = 4
BRANCH = 0.5
EDGE_WIDTH = 3

SHARDS = 44      # splinters thrown clear ahead of the panes
SHARD_SEED = 808
SHARD_REACH = 1200
SHARD_SIZE = 14

ZOOM = 0.07   # how far the splash creeps in on itself while it is held
BARS = 0.085  # how deep each letterbox bar is, as a fraction of the screen
BARS_WAIT = 0.30  # seconds after the glass goes before they start coming in
BARS_IN = 0.55    # and how long they take to reach letterbox
SHUT_AT = 1.85    # a loss does not stop there: when the rest of the way starts
SHUT_IN = 0.62    # and how long the screen takes to close over the result
# the cut itself - the angle, the seam and the geometry - is the intro's,
# and lives in cut.py with it

# victory reads cold and bright, defeat warm and dim
VICTORY = {
    "wash": (26, 34, 92),
    "spoke": (64, 116, 240),
    "glow": (120, 170, 255),
    "text": (255, 236, 140),
    "word": "VICTORY",
    "tilt": -7,
    "glare": (255, 255, 255),  # the blow blows the frame out white...
    "glass": (198, 228, 255),
    "core": (255, 255, 255),
    "shut": 0.0,               # ...and the bars stop at letterbox
}
DEFEAT = {
    "wash": (40, 15, 22),
    "spoke": (104, 32, 46),
    "glow": (150, 60, 70),
    "text": (236, 206, 206),
    "word": "DEFEAT",
    "tilt": 4,
    "glare": (188, 36, 46),    # ...a defeat washes it red instead...
    "glass": (176, 120, 128),
    "core": (236, 206, 206),
    "shut": 1.0,               # ...and the bars keep going until they meet
}

BACKDROP = (0, 0, 0)


def ease_out(progress):
    """0 to 1, quick off the mark and settling at the end."""
    return 1 - (1 - min(1.0, max(0.0, progress))) ** 3


class Outro:
    """Draws the ending. Hand it the age of the result in seconds."""

    def __init__(self, width, height):
        self.size = (width, height)
        self._font = None
        self._figure = None
        self._frozen = None
        self._panes = None
        self._cracks = None
        self._shards = None
        self._scene = None
        self._stage = None

    @property
    def total(self):
        """How long the whole ending runs for."""
        return HIT + CRACK + BREAK + HOLD

    @property
    def middle(self):
        """The point the frame is blown out and broken from."""
        return pygame.Vector2(self.size[0] / 2, self.size[1] / 2)

    # ------------------------------------------------------------- surfaces

    def freeze(self, surface):
        """The last frame of the fight, caught the first time we are drawn."""
        if self._frozen is None:
            self._frozen = surface.copy()
        return self._frozen

    def scene(self):
        if self._scene is None:
            self._scene = pygame.Surface(self.size)
        return self._scene

    def stage(self):
        if self._stage is None:
            self._stage = pygame.Surface(self.size)
        return self._stage

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
        """Paint whichever beat of the ending we are on over the whole frame."""
        look = VICTORY if won else DEFEAT
        frozen = self.freeze(surface)
        scene = self.scene()

        if age < HIT:
            # the blow lands: the fight is still on screen, blown out and kicked
            scene.blit(frozen, (0, 0))
            self.draw_glare(scene, look, 1 - age / HIT)
            self.throw(surface, scene, 1.0)
            return

        since = age - HIT
        if since < CRACK:
            # it is held there a beat while the cracks run out across it
            scene.blit(frozen, (0, 0))
            self.draw_cracks(scene, look, since / CRACK)
            self.throw(surface, scene, math.exp(-since / SETTLE))
            return

        broke = since - CRACK
        self.draw_splash(scene, look, broke)
        if broke < BREAK:
            # the fight falls away off the splash that was behind it
            self.draw_break(scene, look, broke / BREAK)
        self.draw_bars(scene, look, broke)
        surface.blit(scene, (0, 0))

    def draw_glare(self, surface, look, left):
        """The blow-out the blow goes off on, burning off fast."""
        glare = pygame.Surface(self.size)
        glare.fill(look["glare"])
        glare.set_alpha(round(255 * left))
        surface.blit(glare, (0, 0))

    def throw(self, surface, scene, shock):
        """Hand `scene` over kicked into the lens and rattling, `shock` of 1.

        Shoved in further than it is thrown sideways, the way the gun does
        it, so the frame never rattles far enough to show an edge.
        """
        if shock < 0.02:
            surface.blit(scene, (0, 0))
            return
        width, height = self.size
        grown = 1 + PUNCH * shock
        punched = pygame.transform.scale(
            scene, (round(width * grown), round(height * grown))
        )
        throw = KICK * shock
        surface.fill(BACKDROP)
        surface.blit(
            punched,
            punched.get_rect(
                center=(
                    width / 2 + random.uniform(-throw, throw),
                    height / 2 + random.uniform(-throw, throw),
                )
            ),
        )

    # --------------------------------------------------------------- the break

    def cracks(self):
        """The lines that run out from the middle. Built once, so they hold still."""
        if self._cracks is None:
            self._cracks = glass.cracks(
                self.middle,
                math.hypot(*self.size),
                CRACKS,
                CRACK_KINKS,
                CRACK_SEED,
                BRANCH,
            )
        return self._cracks

    def draw_cracks(self, surface, look, grown):
        """The cracks, as far out as they have got: glass, then a lit core."""
        glass.draw_cracks(
            surface, self.cracks(), grown, look["glass"], look["core"], CRACK_WIDTH
        )

    def panes(self, look):
        """The held frame, cracked and cut into panes around the middle."""
        if self._panes is None:
            # the cracks are baked in before it is cut up, so a pane carries
            # its share of them rather than picking up a fresh edge
            broken = self._frozen.copy()
            self.draw_cracks(broken, look, 1.0)
            self._panes = glass.shatter(
                broken, self.middle, PANES, STAGGER, None, EDGE_WIDTH, PANE_SPIN
            )
        return self._panes

    def shards(self):
        """Splinters thrown clear ahead of the panes. Built once."""
        if self._shards is None:
            rolls = random.Random(SHARD_SEED)
            self._shards = [
                {
                    "away": pygame.Vector2(1, 0).rotate(rolls.uniform(0, 360)),
                    "speed": rolls.uniform(0.45, 1.0),
                    "size": SHARD_SIZE * rolls.uniform(0.35, 1.0),
                    "spin": rolls.uniform(-900, 900),
                }
                for _ in range(SHARDS)
            ]
        return self._shards

    def draw_break(self, surface, look, done):
        """The held frame falling away in panes, off whatever is behind it."""
        for pane in self.panes(look):
            image = pygame.transform.rotate(pane["image"], pane["spin"] * done)
            if done > PANE_FADE:
                image.set_alpha(round(255 * (1 - (done - PANE_FADE) / (1 - PANE_FADE))))
            spot = (
                pane["spot"]
                + pane["away"] * FALL * done ** 1.35
                + pygame.Vector2(0, DROP * done ** 2)
            )
            surface.blit(image, image.get_rect(center=spot))

        middle = self.middle
        for shard in self.shards():
            run = done * shard["speed"]
            spot = (
                middle
                + shard["away"] * SHARD_REACH * run ** 0.7
                + pygame.Vector2(0, DROP * run ** 2)
            )
            turn = shard["spin"] * done
            size = shard["size"]
            pygame.draw.polygon(
                surface,
                look["glass"],
                [spot + pygame.Vector2(size, 0).rotate(turn + i * 137) for i in range(3)],
            )

    # -------------------------------------------------------------- the splash

    def draw_splash(self, surface, look, since):
        """The wash, the burst, the figure and the stamp, `since` the glass went.

        It is laid out at full size and then crept in on: the whole splash
        drifts a few per cent closer over the time it is held, so the last
        beat of the battle is never quite still.
        """
        stage = self.stage()
        width, height = self.size

        stage.fill(look["wash"])
        stage.blit(self.burst(look, (HIT + CRACK + since) * SPIN), (0, 0))

        landed = ease_out(since / FIGURE_IN)
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
            stage.blit(grown, grown.get_rect(midbottom=feet))

        stamped = ease_out((since - FIGURE_IN - BANNER_WAIT) / BANNER_IN)
        if stamped > 0:
            word = self.stamp(look, stamped)
            word.set_alpha(round(255 * stamped))
            stage.blit(word, word.get_rect(center=(width * 0.52, height * 0.52)))

        creep = 1 + ZOOM * min(1.0, since / (BREAK + HOLD))
        crept = pygame.transform.scale(
            stage, (round(width * creep), round(height * creep))
        )
        surface.blit(crept, crept.get_rect(center=(width / 2, height / 2)))

    def draw_bars(self, surface, look, since):
        """The intro's two black halves, coming back down over the splash.

        The same cut the battle was let out on, run the other way: `apart`
        walks back from 1 towards 0, so the corners are the first thing the
        black takes and the middle is the last.

        Both endings stop at the band `BARS` leaves open. A win is left
        framed by it; a loss waits until the stamp has been up long enough
        to read, and then the halves carry on until they meet.
        """
        landed = ease_out((since - BARS_WAIT) / BARS_IN)
        if landed <= 0:
            return
        apart = 1 - BARS * landed
        if look["shut"]:
            closing = ease_out((since - SHUT_AT) / SHUT_IN)
            if closing > 0:
                apart *= 1 - closing
        cut.draw_halves(surface, self.size, apart, BACKDROP, look["glow"])
