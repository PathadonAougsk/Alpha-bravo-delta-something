"""MERCY: the battle stops being a battle and becomes Undertale.

Offer the HEADs mercy and they answer the only way they know how. The field,
the wheel and the HUD all drop away, and what is left is a white box with a
red heart in it: the arrows drive the heart, nothing else does anything, and
the bones come in waves until the wave is out. Nothing you can do touches
them - the whole turn is spent not being hit.

Take enough of it and the heart breaks, and that is the game over. Live
through it and the screen blacks out, cracks from the middle and falls away
off the battle it left standing, with the turn back in your hands.
"""

import math
import random

import pygame

import assets
import glass

BACKDROP = (0, 0, 0)
BOX_LINE = (255, 255, 255)  # the box is one white rule on black, like Undertale's
BONE = (255, 255, 255)
TELL_LINE = (128, 128, 132)  # what a shot is drawn as before it is solid
SOUL = (255, 0, 0)
SOUL_CRACK = (255, 190, 190)
HP_LEFT = (255, 220, 40)     # the yellow the HP is counted in
HP_GONE = (160, 36, 36)
TEXT = (255, 255, 255)
CRACK_GLASS = (198, 228, 255)  # the same blue-white the gun breaks the screen in

OPEN = 0.40      # seconds the box takes to open out of nothing
WAVE = 4.0       # seconds the wave runs, before the share each HEAD adds
PER_HEAD = 1.3
WAVE_CAP = 10.0  # however big the formation, the turn has to end some time
CLOSE = 0.55     # the beat after the last volley, with what is up still live

BOX = (380, 300)     # how big the box is...
BOX_AT = (0.5, 0.52)  # ...and where it sits, as a fraction of the screen
BOX_LINE_WIDTH = 5
RUNUP = 150  # how far outside the box a shot is still drawn, so you see it coming
TIMER_WIDTH = 4      # the line along the top of the box that drains with the wave

SOUL_SIZE = 11   # half-height of the heart as it is drawn
SOUL_HIT = 6     # and the half-width of it that can actually be hit
SOUL_SPEED = 250  # pixels a second it moves at
GRACE = 0.85     # seconds nothing can touch you for after a hit
FLICKER = 14     # how fast the heart blinks over those seconds

BONE_WIDTH = 13     # how thick a bone is across the short way
BONE_SPEED = 215
PELLET = 10         # across, for the aimed shots
PELLET_SPEED = 190
TELL = 0.42         # seconds an aimed shot hangs there as a warning first
VOLLEY = 1.15       # seconds between volleys at the top of the wave...
VOLLEY_TIGHT = 0.55  # ...and what that closes to by the end of it
LANES = 6           # columns a falling volley is split into
ROWS = 5            # and rows a sweeping one is

BREAK_HOLD = 0.55  # seconds the cracked heart hangs there before it gives
BREAK_FALL = 1.25  # and how long the pieces take to fall out of the screen
SHARDS = 9
SHARD_FLY = 430    # pixels a piece is thrown up and out
SHARD_DROP = 1100  # and how hard gravity takes it back
SHARD_SIZE = 0.8   # the biggest a piece is, against the heart it came off

BLACK = 0.30   # seconds the screen sits black before it cracks
CRACK = 0.50   # seconds the cracks take to cross it
FALL = 0.70    # seconds the black takes to fall off the battle underneath
CRACKS = 18
CRACK_SEED = 77
CRACK_KINKS = 5
CRACK_WIDTH = 4
BRANCH = 0.5
PANES = 15
PANE_FALL = 900
PANE_DROP = 700
PANE_SPIN = 90
PANE_FADE = 0.7  # the fraction of the fall a pane flies for before fading out

# the phases, in the order they happen; BREAKING and LEAVING are the two ways out
OPENING = "opening"
DODGING = "dodging"
BREAKING = "breaking"
LEAVING = "leaving"
OVER = "over"

LEFT = (pygame.K_LEFT, pygame.K_a)
RIGHT = (pygame.K_RIGHT, pygame.K_d)
UP = (pygame.K_UP, pygame.K_w)
DOWN = (pygame.K_DOWN, pygame.K_s)


def ease_out(progress):
    """0 to 1, quick off the mark and settling at the end."""
    return 1 - (1 - min(1.0, max(0.0, progress))) ** 3


def held(keys, group):
    """True while any key in `group` is down."""
    return any(keys[key] for key in group)


class Shot:
    """One thing in the air: a bone, or a pellet when it is drawn round.

    It sits still while `tell` runs down - that is the warning, drawn hollow -
    and only then goes live and starts travelling. Volleys that come in from
    outside the box need no warning: you watch them arrive.
    """

    def __init__(self, spot, drift, size, tell=0.0, pellet=False):
        self.spot = pygame.Vector2(spot)
        self.drift = pygame.Vector2(drift)
        self.size = size
        self.tell = tell
        self.pellet = pellet

    @property
    def live(self):
        """False while it is still only a warning, and cannot hit anything."""
        return self.tell <= 0

    @property
    def rect(self):
        box = pygame.Rect(0, 0, round(self.size[0]), round(self.size[1]))
        box.center = (round(self.spot.x), round(self.spot.y))
        return box

    def advance(self, dt):
        if self.tell > 0:
            self.tell -= dt
            return
        self.spot += self.drift * dt

    def draw(self, surface):
        rect = self.rect
        if not self.live:
            if self.pellet:
                pygame.draw.circle(surface, TELL_LINE, self.spot, self.size[0] / 2, 2)
            else:
                pygame.draw.rect(surface, TELL_LINE, rect, 2)
            return
        if self.pellet:
            pygame.draw.circle(surface, BONE, self.spot, self.size[0] / 2)
            return
        pygame.draw.rect(surface, BONE, rect)
        # the knobs on the ends, so a bone reads as a bone and not as a bar
        knob = min(self.size) * 0.8
        if self.size[1] >= self.size[0]:
            ends = ((rect.centerx, rect.top), (rect.centerx, rect.bottom))
        else:
            ends = ((rect.left, rect.centery), (rect.right, rect.centery))
        for end in ends:
            pygame.draw.circle(surface, BONE, end, knob)


class Mercy:
    """The dodging box. `begin` a wave, advance it every frame, read `done`.

    Unlike the gun this is not a one-shot: MERCY can be picked every turn, so
    every wave is built fresh and the old one is thrown away with it.
    """

    def __init__(self, width, height):
        self.size = (width, height)
        self.live = False
        self.phase = OVER
        self.beat = 0.0
        self.player = None
        self.shots = []
        self.taken = 0
        self.survived = True

    # -------------------------------------------------------------- progress

    def begin(self, player, enemies):
        """Start a fresh wave against whoever is still standing."""
        living = [enemy for enemy in enemies if enemy.alive] or list(enemies)
        self.player = player
        self.live = True
        self.phase = OPENING
        self.beat = 0.0
        self.shots = []
        self.taken = 0
        self.survived = True
        self.rolls = random.Random()
        self.heart = pygame.Vector2(self.box().center)
        self.grace = 0.0
        self.wait = TELL + 0.3  # the first volley does not arrive instantly
        self.last = None        # the pattern that came up last, so none repeats
        self.length = min(WAVE_CAP, WAVE + PER_HEAD * len(living))
        # a bone bites for what the average HEAD swings for, so the wave is
        # as dangerous as the formation it came out of
        self.bite = max(
            1, round(sum(e.attack_damage for e in living) / max(1, len(living)))
        )
        self._shards = None
        self._cracks = None
        self._panes = None

    def step(self, phase):
        self.phase = phase
        self.beat = 0.0

    @property
    def done(self):
        return self.phase == OVER

    @property
    def covering(self):
        """True while MERCY owns the whole screen.

        It lets go for the last beat of all: the battle is drawn again
        underneath and the black falls off it in panes.
        """
        if not self.live:
            return False
        if self.phase == LEAVING:
            return self.beat < BLACK + CRACK
        return True

    def clear(self):
        """The result has been taken; the box is no longer anything's business."""
        self.live = False
        self.shots = []

    # ----------------------------------------------------------------- shape

    def box(self):
        """The white box the whole turn happens inside."""
        return pygame.Rect(
            round(self.size[0] * BOX_AT[0] - BOX[0] / 2),
            round(self.size[1] * BOX_AT[1] - BOX[1] / 2),
            BOX[0],
            BOX[1],
        )

    def hitbox(self):
        """The part of the heart that actually gets hit - smaller than it looks."""
        box = pygame.Rect(0, 0, SOUL_HIT * 2, SOUL_HIT * 2)
        box.center = (round(self.heart.x), round(self.heart.y))
        return box

    # -------------------------------------------------------------- the wave

    def advance(self, dt, keys=None):
        """Step the box on. `keys` is a pygame key state; it drives the heart."""
        if not self.live:
            return
        self.beat += dt

        if self.phase == OPENING:
            if self.beat >= OPEN:
                self.step(DODGING)

        elif self.phase == DODGING:
            if keys is not None:
                self.drive(keys, dt)
            self.fire(dt)
            self.fly(dt)
            if self.phase == DODGING and self.beat >= self.length + CLOSE:
                self.step(LEAVING)  # the wave is out and the heart is still going

        elif self.phase == BREAKING:
            if self.beat >= BREAK_HOLD + BREAK_FALL:
                self.step(OVER)

        elif self.phase == LEAVING:
            if self.beat >= BLACK + CRACK + FALL:
                self.step(OVER)

    def drive(self, keys, dt):
        """The arrows move the heart, and the box is as far as it goes."""
        move = pygame.Vector2(
            held(keys, RIGHT) - held(keys, LEFT),
            held(keys, DOWN) - held(keys, UP),
        )
        if move.length_squared():
            self.heart += move.normalize() * SOUL_SPEED * dt
        inside = self.box().inflate(-SOUL_SIZE * 2, -SOUL_SIZE * 2)
        self.heart.x = min(max(self.heart.x, inside.left), inside.right)
        self.heart.y = min(max(self.heart.y, inside.top), inside.bottom)

    def fire(self, dt):
        """Put the next volley up, on a cadence that tightens as the wave runs."""
        if self.beat >= self.length:
            return  # the wave is spent; what is already up still has to be dodged
        self.wait -= dt
        if self.wait > 0:
            return
        run = self.beat / self.length
        self.wait = VOLLEY + (VOLLEY_TIGHT - VOLLEY) * run

        patterns = [self.rain, self.sweep, self.closing]
        if self.last in patterns and len(patterns) > 1:
            patterns.remove(self.last)  # never the same thing twice running
        self.last = self.rolls.choice(patterns)
        self.shots.extend(self.last())

    def fly(self, dt):
        """Move everything that is up, and see what got through."""
        self.grace = max(0.0, self.grace - dt)
        reach = pygame.Rect((0, 0), self.size).inflate(400, 400)
        live = []
        for shot in self.shots:
            shot.advance(dt)
            if not reach.colliderect(shot.rect):
                continue  # gone past the screen; it is nobody's problem now
            live.append(shot)
            if shot.live and not self.grace and shot.rect.colliderect(self.hitbox()):
                self.wound()
        self.shots = live

    def wound(self):
        """A bone got through. The heart takes it, and flickers for a beat."""
        before = self.player.health
        self.player.take_damage(self.bite)
        self.taken += before - self.player.health
        self.grace = GRACE
        if not self.player.alive:
            self.survived = False
            self.grace = 0.0  # the last one does not flicker; it breaks
            self.step(BREAKING)

    # ----------------------------------------------------------- the volleys

    def rain(self):
        """Bones dropping in through the roof, with a column left open."""
        box = self.box()
        gap = self.rolls.randrange(LANES)
        step = box.width / LANES
        bones = []
        for i in range(LANES):
            if i == gap:
                continue
            length = self.rolls.uniform(50, 120)
            bones.append(
                Shot(
                    (box.left + step * (i + 0.5), box.top - length),
                    (0, BONE_SPEED * self.rolls.uniform(0.85, 1.2)),
                    (BONE_WIDTH, length),
                )
            )
        return bones

    def sweep(self):
        """A rank of bones sliding in from one side, with a row to slip through."""
        box = self.box()
        gap = self.rolls.randrange(ROWS)
        step = box.height / ROWS
        from_left = self.rolls.random() < 0.5
        bones = []
        for i in range(ROWS):
            if i == gap:
                continue
            length = self.rolls.uniform(60, 130)
            speed = BONE_SPEED * self.rolls.uniform(0.8, 1.1)
            bones.append(
                Shot(
                    (
                        box.left - length if from_left else box.right + length,
                        box.top + step * (i + 0.5),
                    ),
                    (speed if from_left else -speed, 0),
                    (length, BONE_WIDTH),
                )
            )
        return bones

    def closing(self):
        """Pellets around the rim, every one of them aimed at where you are now.

        They hang there hollow for a moment before they come, which is the
        whole pattern: the aim is taken when they appear, so the warning is
        long enough to walk out of.
        """
        box = self.box()
        aim = pygame.Vector2(self.heart)
        shots = []
        count = self.rolls.randint(5, 8)
        for i in range(count):
            angle = math.tau * (i + self.rolls.uniform(0, 0.6)) / count
            spot = pygame.Vector2(box.center) + pygame.Vector2(
                math.cos(angle) * box.width * 0.62, math.sin(angle) * box.height * 0.62
            )
            run = aim - spot
            drift = (
                run.normalize() * PELLET_SPEED
                if run.length_squared()
                else pygame.Vector2(0, PELLET_SPEED)
            )
            shots.append(Shot(spot, drift, (PELLET, PELLET), tell=TELL, pellet=True))
        return shots

    # --------------------------------------------------------------- drawing

    def draw(self, surface):
        """Paint whichever beat of the box we are on."""
        if not self.live or self.phase == OVER:
            return

        if self.phase == OPENING:
            surface.fill(BACKDROP)
            self.draw_box(surface, ease_out(self.beat / OPEN))
            self.draw_soul(surface, self.heart)
            self.draw_hp(surface)
            self.draw_lines(surface)

        elif self.phase == DODGING:
            surface.fill(BACKDROP)
            self.draw_box(surface, 1.0, left=1 - min(1.0, self.beat / self.length))
            kept = surface.get_clip()
            surface.set_clip(self.box().inflate(RUNUP * 2, RUNUP * 2))
            for shot in self.shots:
                shot.draw(surface)
            surface.set_clip(kept)
            self.draw_soul(surface, self.heart)
            self.draw_hp(surface)
            self.draw_lines(surface)

        elif self.phase == BREAKING:
            surface.fill(BACKDROP)
            self.draw_break(surface)

        elif self.phase == LEAVING:
            self.draw_leave(surface)

    def draw_box(self, surface, grown, left=None):
        """The white rule the fight happens inside, opening out of its own middle."""
        box = self.box()
        if grown < 1:
            box = pygame.Rect(
                box.x, 0, box.width, max(BOX_LINE_WIDTH * 2, round(box.height * grown))
            )
            box.centery = self.box().centery
        pygame.draw.rect(surface, BOX_LINE, box, BOX_LINE_WIDTH)
        if left is None:
            return
        # how much of the turn is left, drained along the top rule: Undertale
        # does not show it, but Undertale tells you when the wave is over
        pygame.draw.rect(
            surface,
            BACKDROP,
            (box.x, box.y - TIMER_WIDTH - 4, box.width, TIMER_WIDTH),
        )
        pygame.draw.rect(
            surface,
            BOX_LINE,
            (box.x, box.y - TIMER_WIDTH - 4, round(box.width * left), TIMER_WIDTH),
        )

    def draw_soul(self, surface, spot, size=SOUL_SIZE, color=SOUL):
        """The heart: two lobes and a point, the way a soul is drawn."""
        if self.grace and int(self.grace * FLICKER) % 2:
            return  # the flicker after a hit: it blinks out and back
        pygame.draw.circle(surface, color, (spot.x - size * 0.46, spot.y - size * 0.3), size * 0.54)
        pygame.draw.circle(surface, color, (spot.x + size * 0.46, spot.y - size * 0.3), size * 0.54)
        pygame.draw.polygon(
            surface,
            color,
            [
                (spot.x - size * 0.95, spot.y - size * 0.18),
                (spot.x + size * 0.95, spot.y - size * 0.18),
                (spot.x, spot.y + size),
            ],
        )

    def draw_hp(self, surface):
        """The HP strip under the box, counted the way the box counts it."""
        box = self.box()
        font = assets.font(26)
        label = font.render("HP", True, TEXT)
        health = max(0, self.player.health)
        count = font.render(f"{health} / {self.player.max_health}", True, TEXT)
        bar = pygame.Rect(0, 0, 170, 16)
        width = label.get_width() + 10 + bar.width + 10 + count.get_width()

        left = box.centerx - width / 2
        middle = box.bottom + 28
        surface.blit(label, label.get_rect(midleft=(left, middle)))
        bar.midleft = (left + label.get_width() + 10, middle)
        pygame.draw.rect(surface, HP_GONE, bar)
        pygame.draw.rect(
            surface,
            HP_LEFT,
            (bar.x, bar.y, round(bar.width * health / self.player.max_health), bar.height),
        )
        surface.blit(count, count.get_rect(midleft=(bar.right + 10, middle)))

    def draw_lines(self, surface):
        """What the box has to say, in the asterisks it says everything in."""
        font = assets.font(24)
        said = ["* The HEADs answer."]
        if self.phase == OPENING or self.beat < 2.4:
            said.append("* Arrows move the heart. Nothing else moves.")
        for i, line in enumerate(said):
            surface.blit(font.render(line, True, TEXT), (40, 36 + i * 28))

    # ------------------------------------------------------- the heart going

    def shards(self):
        """The pieces the heart comes apart into. Built once, when it goes."""
        if self._shards is None:
            rolls = self.rolls
            self._shards = [
                {
                    # up and out: it bursts before gravity gets hold of it
                    "away": pygame.Vector2(1, 0).rotate(rolls.uniform(-168, -12)),
                    "speed": rolls.uniform(0.45, 1.0),
                    "spin": rolls.uniform(-540, 540),
                    "size": SOUL_SIZE * rolls.uniform(0.34, SHARD_SIZE),
                }
                for _ in range(SHARDS)
            ]
        return self._shards

    def draw_break(self, surface):
        """The heart cracking, hanging there a moment, and then going."""
        if self.beat < BREAK_HOLD:
            left = max(0.0, 1 - self.beat / BREAK_HOLD)
            pygame.draw.rect(  # the box goes out from under it
                surface,
                tuple(round(c * left) for c in BOX_LINE),
                self.box(),
                BOX_LINE_WIDTH,
            )
            self.draw_soul(surface, self.heart)
            self.draw_hp(surface)
            self.draw_split(surface)
            return

        done = min(1.0, (self.beat - BREAK_HOLD) / BREAK_FALL)
        for shard in self.shards():
            run = done * shard["speed"]
            spot = (
                self.heart
                + shard["away"] * SHARD_FLY * run ** 0.6  # it bursts, then slows
                + pygame.Vector2(0, SHARD_DROP * run ** 2)
            )
            turn = shard["spin"] * done
            size = shard["size"]
            pygame.draw.polygon(
                surface,
                SOUL,
                [spot + pygame.Vector2(size, 0).rotate(turn + i * 137) for i in range(3)],
            )

    def draw_split(self, surface):
        """The crack down the heart, there for the beat before it gives."""
        x, y = self.heart
        pygame.draw.lines(
            surface,
            SOUL_CRACK,
            False,
            [
                (x + SOUL_SIZE * 0.16, y - SOUL_SIZE),
                (x - SOUL_SIZE * 0.22, y - SOUL_SIZE * 0.3),
                (x + SOUL_SIZE * 0.26, y + SOUL_SIZE * 0.1),
                (x - SOUL_SIZE * 0.1, y + SOUL_SIZE),
            ],
            2,
        )

    # ----------------------------------------------------- the way back out

    def cracks(self):
        """The cracks that cross the black on the way back to the battle."""
        if self._cracks is None:
            middle = (self.size[0] / 2, self.size[1] / 2)
            self._cracks = glass.cracks(
                middle,
                math.hypot(*self.size),
                CRACKS,
                CRACK_KINKS,
                CRACK_SEED,
                BRANCH,
            )
        return self._cracks

    def panes(self):
        """That cracked black, cut into panes and ready to fall off the battle."""
        if self._panes is None:
            frozen = pygame.Surface(self.size)
            frozen.fill(BACKDROP)
            glass.draw_cracks(
                frozen, self.cracks(), 1.0, CRACK_GLASS, BOX_LINE, CRACK_WIDTH
            )
            self._panes = glass.shatter(
                frozen,
                (self.size[0] / 2, self.size[1] / 2),
                PANES,
                edge=CRACK_GLASS,
                spin=PANE_SPIN,
            )
        return self._panes

    def draw_leave(self, surface):
        """Black, then cracks across it, then the black falling off the battle.

        Only the last of those three is drawn over anything: by then the
        caller has put the field, the HUD and the message back underneath.
        """
        if self.beat < BLACK:
            surface.fill(BACKDROP)
            return

        if self.beat < BLACK + CRACK:
            surface.fill(BACKDROP)
            glass.draw_cracks(
                surface,
                self.cracks(),
                (self.beat - BLACK) / CRACK,
                CRACK_GLASS,
                BOX_LINE,
                CRACK_WIDTH,
            )
            return

        done = min(1.0, (self.beat - BLACK - CRACK) / FALL)
        for pane in self.panes():
            image = pygame.transform.rotate(pane["image"], pane["spin"] * done)
            if done > PANE_FADE:
                image.set_alpha(round(255 * (1 - (done - PANE_FADE) / (1 - PANE_FADE))))
            spot = (
                pane["spot"]
                + pane["away"] * PANE_FALL * done ** 1.4
                + pygame.Vector2(0, PANE_DROP * done ** 2)
            )
            surface.blit(image, image.get_rect(center=spot))
