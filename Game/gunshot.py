"""The gun: what the screen does on the way out.

Everything drops away - the field, the HUD, the colour - and the player is
left in the middle of a black screen as a flat white cut-out with the gun
raised to their head. The black throbs while it is held there and the hand
starts to go. The shot takes the screen with them: a white-out, a burst of
light tearing out of the muzzle and a ring running off to the corners, the
whole frame kicked into the lens and rattling, then cracks racing out and the
frame coming apart into panes of glass that turn over as they fall out of shot
behind a spray of splinters, leaving nothing. The battle is lost by the time
the last one is gone.
"""

import math
import random

import pygame

import assets
import glass

FIGURE = (255, 255, 255)  # the cut-out is flat white, the way the intro's is flat blue
BACKDROP = (0, 0, 0)
GLASS = (198, 228, 255)   # the blue-white a broken edge catches the light in

RAISE = 0.70   # seconds the cut-out takes to come up out of the black
AIM = 0.60     # the beat it stands there with the gun up
FLASH = 0.22   # the white-out the shot goes off on
FLASH_HOLD = 0.45  # the fraction of that the frame stays blown right out for
CRACK = 0.26   # seconds the cracks take to run to the edges
BREAK = 0.95   # seconds the panes take to fall out of the frame

HEIGHT_FILL = 0.74    # how much of the screen the cut-out stands up
HEAD = (0.52, 0.13)   # where the muzzle sits, as a fraction of the cut-out
RISE_PIXELS = 46      # how far it comes up as it fades in

GUN_LENGTH = 64       # the little white pistol held to the head
GUN_THICK = 14
GUN_GRIP = 26
GUN_KEYLINE = 3       # dark edge, so white-on-white still reads as a gun
GUN_REACH = 24        # how far out from the temple the muzzle is held

SHIVER = 9     # pixels the cut-out judders by in the last of the beat it aims
PULSE = 54     # how far the black throbs up towards red while the gun is held
BEATS = 3      # heartbeats in that beat, quickening towards the shot

KICK = 30      # pixels the whole frame is thrown about by the shot
PUNCH = 0.13   # and how far it is shoved into the lens with it
SETTLE = 0.42  # seconds that kick takes to fall away

BURST = 0.30      # seconds the light out of the muzzle burns for
SPIKES = 22       # how many spikes it tears out in
SPIKE_REACH = 420
SPIKE_SEED = 613  # the spikes are rolled once and then held still
RING = 0.42       # seconds the shockwave takes to run off the corners
RING_WIDTH = 16   # how heavy that ring starts, thinning to nothing as it goes

PANES = 19        # how many panes the screen comes apart into
STAGGER = 0.45    # how far a pane's edge wanders off an even slice, 0 to 1
FALL = 1150       # pixels a pane travels out of the frame
DROP = 900        # and how far gravity drags it down on the way
SPIN = 140        # degrees it turns as it goes
EDGE_WIDTH = 3    # how heavy the lit edge of a pane is drawn
FADE = 0.68       # the fraction of the fall it flies for before fading out

CRACKS = 24        # lines running out from the muzzle
CRACK_SEED = 1917  # the cracks are rolled once and then held still
CRACK_KINKS = 6    # segments each one breaks into
CRACK_WIDTH = 4    # the glass underlay; a white core is laid down inside it
BRANCH = 0.55      # the chance a crack throws a second line off one of its kinks

SHARDS = 70        # splinters thrown clear of the muzzle ahead of the panes
SHARD_SEED = 404
SHARD_REACH = 1400
SHARD_SIZE = 16


def ease_out(progress):
    """0 to 1, quick off the mark and settling at the end."""
    return 1 - (1 - min(1.0, max(0.0, progress))) ** 3


class Gunshot:
    """The cut-in. Advance it every frame and draw it until it is `done`."""

    def __init__(self, width, height):
        self.size = (width, height)
        self.age = 0.0
        self._figure = None
        self._panes = None
        self._cracks = None
        self._spikes = None
        self._shards = None
        self._scene = None

    # -------------------------------------------------------------- progress

    def advance(self, dt):
        self.age += dt

    @property
    def shot_at(self):
        return RAISE + AIM

    @property
    def total(self):
        return RAISE + AIM + CRACK + BREAK

    @property
    def fired(self):
        return self.age >= self.shot_at

    @property
    def done(self):
        return self.age >= self.total

    # ----------------------------------------------------------------- parts

    def figure(self):
        """The player's outline, filled flat white. Built once."""
        if self._figure is None:
            sprite = assets.by_height(
                assets.PLAYER, round(self.size[1] * HEIGHT_FILL)
            )
            if sprite is None:
                return None
            # the mask is the sprite's own shape, so the silhouette is exact
            shape = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
            pygame.mask.from_surface(sprite).to_surface(
                shape, setcolor=FIGURE, unsetcolor=(0, 0, 0, 0)
            )
            self._figure = shape
        return self._figure

    def figure_rect(self, lift=0.0):
        """Where the cut-out stands: dead centre, `lift` pixels below its mark."""
        figure = self.figure()
        width, height = self.size
        if figure is None:
            return pygame.Rect(width // 2, height // 2, 0, 0)
        return figure.get_rect(center=(width / 2, height * 0.54 + lift))

    def muzzle(self):
        """The point the shot goes off at, and everything cracks from."""
        rect = self.figure_rect()
        if not rect.width:
            return pygame.Vector2(self.size[0] / 2, self.size[1] * 0.3)
        return pygame.Vector2(
            rect.left + rect.width * HEAD[0], rect.top + rect.height * HEAD[1]
        )

    def scene(self):
        """The frame everything is painted on before the kick throws it about."""
        if self._scene is None:
            self._scene = pygame.Surface(self.size)
        return self._scene

    # --------------------------------------------------------------- drawing

    def draw(self, surface, player=None):
        """Paint whichever beat of the cut-in we are on over the whole frame."""
        scene = self.scene()

        if self.age < RAISE:
            landed = ease_out(self.age / RAISE)
            self.draw_stage(scene, fade=landed, lift=RISE_PIXELS * (1 - landed))
            surface.blit(scene, (0, 0))
            return

        if not self.fired:
            held = (self.age - RAISE) / AIM
            self.draw_stage(scene, armed=True, shiver=held, pulse=held)
            surface.blit(scene, (0, 0))
            return

        since = self.age - self.shot_at
        if since < CRACK:
            self.draw_stage(scene, armed=True)
            self.draw_cracks(scene, since / CRACK)
        else:
            self.draw_break(scene, min(1.0, (since - CRACK) / BREAK))

        self.draw_shot(scene, since)  # the shot itself, burning off fast
        self.throw(surface, scene, math.exp(-since / SETTLE))

    def backdrop(self, pulse):
        """The black, lifted towards red on a heartbeat as the gun is held."""
        if pulse <= 0:
            return BACKDROP
        beat = (math.sin(pulse ** 2 * BEATS * math.tau) + 1) / 2
        lit = PULSE * beat * pulse ** 2
        return (round(lit), round(lit * 0.22), round(lit * 0.22))

    def draw_stage(self, surface, fade=1.0, lift=0.0, armed=False, shiver=0.0, pulse=0.0):
        """The black screen with the white cut-out standing in the middle of it."""
        surface.fill(self.backdrop(pulse))
        figure = self.figure()
        if figure is None:
            return
        if fade < 1:
            figure = figure.copy()
            figure.set_alpha(round(255 * fade))
        # the hand goes at the end: the whole cut-out judders on the spot
        rattle = pygame.Vector2()
        if shiver:
            reach = SHIVER * shiver ** 2
            rattle.update(random.uniform(-reach, reach), random.uniform(-reach, reach))
        surface.blit(figure, self.figure_rect(lift).move(rattle))
        if armed:
            self.draw_gun(surface, self.muzzle() + rattle)

    def draw_gun(self, surface, muzzle):
        """The pistol, held to the temple with the barrel pointing back at it.

        It is white on a white head, so it is laid down twice: a dark keyline
        first, the shape itself inset into it. That way the barrel still reads
        where it crosses the cut-out, and the grip reads against the black.
        """
        pad = GUN_KEYLINE
        gun = pygame.Surface(
            (GUN_LENGTH + pad * 2, GUN_THICK + GUN_GRIP + pad * 2), pygame.SRCALPHA
        )
        for color, inset in ((BACKDROP, 0), (FIGURE, pad)):
            edge = pad - inset
            pygame.draw.rect(
                gun, color, (inset, inset, GUN_LENGTH + edge * 2, GUN_THICK + edge * 2)
            )
            pygame.draw.rect(
                gun,
                color,
                (
                    inset + GUN_LENGTH - GUN_GRIP,
                    inset + GUN_THICK,
                    GUN_GRIP - 4 + edge * 2,
                    GUN_GRIP + edge,
                ),
            )
        # the muzzle end is held off the temple, so the body of it is in the black
        surface.blit(gun, (muzzle.x + GUN_REACH, muzzle.y - GUN_THICK))

    # --------------------------------------------------------------- the shot

    def throw(self, surface, scene, shock):
        """Hand `scene` over kicked into the lens and rattling, `shock` of 1.

        It is shoved in further than it is thrown sideways, so the frame never
        rattles far enough to show an edge: the screen itself takes the hit.
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

    def draw_shot(self, surface, since):
        """The burst out of the muzzle, the shockwave, and the white-out."""
        muzzle = self.muzzle()
        if since < BURST:
            self.draw_burst(surface, muzzle, since / BURST)
        if since < RING:
            self.draw_ring(surface, muzzle, since / RING)
        if since < FLASH:
            part = since / FLASH
            left = (
                1.0
                if part < FLASH_HOLD
                else 1 - (part - FLASH_HOLD) / (1 - FLASH_HOLD)
            )
            glare = pygame.Surface(self.size)
            glare.fill((255, 255, 255))
            glare.set_alpha(round(255 * left))
            surface.blit(glare, (0, 0))

    def spikes(self):
        """The angles and reaches the muzzle throws light out at. Built once."""
        if self._spikes is None:
            rolls = random.Random(SPIKE_SEED)
            step = math.tau / SPIKES
            self._spikes = [
                (
                    i * step + rolls.uniform(-step / 2, step / 2),
                    SPIKE_REACH * rolls.uniform(0.35, 1.0),
                )
                for i in range(SPIKES)
            ]
        return self._spikes

    def draw_burst(self, surface, muzzle, grown):
        """Spikes of white tearing out of the muzzle, burning off as they go."""
        out = ease_out(grown)
        left = round(255 * (1 - grown) ** 2)
        burst = pygame.Surface(self.size, pygame.SRCALPHA)
        for angle, reach in self.spikes():
            tip = muzzle + pygame.Vector2(math.cos(angle), math.sin(angle)) * reach * out
            pygame.draw.line(
                burst, (255, 255, 255, left), muzzle, tip, max(1, round(7 * (1 - grown)))
            )
        pygame.draw.circle(  # the muzzle itself, blown out and closing up
            burst, (255, 255, 255, left), muzzle, max(1, round(70 * (1 - grown ** 0.6)))
        )
        surface.blit(burst, (0, 0))

    def draw_ring(self, surface, muzzle, grown):
        """The shockwave: one hard ring of light running off to the corners."""
        reach = math.hypot(*self.size)
        width = max(1, round(RING_WIDTH * (1 - grown)))
        ring = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.circle(
            ring,
            (*GLASS, round(255 * (1 - grown))),
            muzzle,
            max(width, round(reach * ease_out(grown))),
            width,
        )
        surface.blit(ring, (0, 0))

    # ------------------------------------------------------------- the break

    def cracks(self):
        """The lines that run out from the muzzle. Built once, so they hold still."""
        if self._cracks is None:
            self._cracks = glass.cracks(
                self.muzzle(),
                math.hypot(*self.size),
                CRACKS,
                CRACK_KINKS,
                CRACK_SEED,
                BRANCH,
            )
        return self._cracks

    def draw_cracks(self, surface, grown):
        """The cracks, drawn as far out as they have got: glass, then a hot core."""
        glass.draw_cracks(surface, self.cracks(), grown, GLASS, FIGURE, CRACK_WIDTH)

    def panes(self):
        """The screen, frozen at the shot and cut into panes around the muzzle."""
        if self._panes is None:
            frozen = pygame.Surface(self.size)
            self.draw_stage(frozen, armed=True)
            self._panes = glass.shatter(
                frozen, self.muzzle(), PANES, STAGGER, GLASS, EDGE_WIDTH, SPIN
            )
        return self._panes

    def shards(self):
        """Splinters thrown clear of the muzzle ahead of the panes. Built once."""
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

    def draw_shards(self, surface, done):
        """The splinters, tumbling out past the edges of the frame."""
        muzzle = self.muzzle()
        for shard in self.shards():
            run = done * shard["speed"]
            spot = (
                muzzle
                + shard["away"] * SHARD_REACH * run ** 0.7
                + pygame.Vector2(0, DROP * run ** 2)
            )
            turn = shard["spin"] * done
            size = shard["size"]
            pygame.draw.polygon(
                surface,
                GLASS,
                [spot + pygame.Vector2(size, 0).rotate(turn + i * 137) for i in range(3)],
            )

    def draw_break(self, surface, done):
        """The panes falling out of the frame, `done` of the way through."""
        surface.fill(BACKDROP)
        for pane in self.panes():
            image = pygame.transform.rotate(pane["image"], pane["spin"] * done)
            if done > FADE:
                image.set_alpha(round(255 * (1 - (done - FADE) / (1 - FADE))))
            spot = (
                pane["spot"]
                + pane["away"] * FALL * done ** 1.35
                + pygame.Vector2(0, DROP * done ** 2)
            )
            surface.blit(image, image.get_rect(center=spot))
        self.draw_shards(surface, done)
