"""DETERMINATION: the battle stops being a battle and becomes Undertale.

Dig your heels in and the HEADs answer the only way they know how. The
field, the wheel and the HUD all drop away, and what is left is a white box with a
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
import textbox

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
WAVE = 5.0       # seconds the wave runs, before the share each HEAD adds
PER_HEAD = 1.7
WAVE_CAP = 13.0  # however big the formation, the turn has to end some time
CLOSE = 0.55     # the beat after the last volley, with what is up still live

BOX = (380, 300)     # how big the box is...
BOX_AT = (0.5, 0.52)  # ...and where it sits, as a fraction of the screen
BOX_LINE_WIDTH = 5
RUNUP = 150  # how far outside the box a shot is still drawn, so you see it coming
TIMER_WIDTH = 4      # the line along the top of the box that drains with the wave

SOUL_SIZE = 11   # half-height of the heart as it is drawn
SOUL_HIT = 6     # and the half-width of it that can actually be hit
SOUL_SPEED = 285  # pixels a second it moves at
GRACE = 0.85     # seconds nothing can touch you for after a hit
FLICKER = 14     # how fast the heart blinks over those seconds

BONE_WIDTH = 13     # how thick a bone is across the short way
BONE_SPEED = 260
PELLET = 10         # across, for the aimed shots
PELLET_SPEED = 225
TELL = 0.38         # seconds an aimed shot hangs there as a warning first
VOLLEY = 0.95       # seconds between volleys at the top of the wave...
VOLLEY_TIGHT = 0.44  # ...and what that closes to by the end of it
LANES = 6           # columns a falling volley is split into
ROWS = 5            # and rows a sweeping one is

# The walls, which are where this stops being a warm-up: a rank of bone the
# depth of the box with one slot in it to be lined up with, and a blue one
# with no slot at all - because a blue bone only bites what moves, so the way
# through it is to take your hands off the arrows and let it pass.
BLUE = (100, 190, 255)
WALL_WIDTH = 17
WALL_GAP = 80         # the slot left in a white wall, in pixels
WALL_SPEED = 290
BLUE_WALL_WIDTH = 26
BLUE_WALL_SPEED = 300
BLUE_LEAD = 0.9       # how far outside the box a blue wall starts, in box widths
BLUE_CLEAR = 0.25     # seconds after a blue wall is through before anything else
WALL_CLEAR = 0.6      # the share of a white wall's crossing it gets to itself

# The skulls. They do not travel: they line up on the row or the column you
# are standing in, charge where you can see them charging, and then the beam
# is simply on. The charge is the whole attack - once it is firing there is
# nothing to do about it but already be somewhere else.
BLASTER_TELL = 0.55  # seconds the skull hangs there before it fires
BLASTER_CLEAR = 0.2  # and the beat after that before anything else arrives
BEAM_TIME = 0.55     # and how long the beam is up for
BEAM_WIDTH = 40
BEAM_OVER = 60       # how far past the far side of the box the beam carries
BEAM_CORE = (255, 255, 255)
BEAM_EDGE = (185, 215, 255)
SKULL = (62, 46)     # how big the head is drawn, pointing right
SKULL_GAP = 44       # how far outside the box it sits
SKULL_RUSH = 0.55    # how small it arrives, against how big it ends up

# How far into the wave each tier of this is allowed to start. The opening is
# bones; the skulls and the walls are what it turns into.
HARDER_AT = 0.3   # the share of the wave the skulls come out after...
HARDEST_AT = 0.5  # ...and the share the blue walls do

LOW_HP = 40          # at or under this the box stops narrating and starts talking
DETERMINED = (255, 240, 170)  # the warm off-white those lines are said in
MURMUR_LINE = 1.15   # seconds before the next line of one comes up
MURMUR_FADE = 0.55   # seconds a line takes to arrive
MURMUR_PULSE = 2.6   # radians a second the whole thing breathes at
MURMUR_FLOOR = 0.60  # the dimmest that breath takes it

# What the box finds to say when there is almost nothing left. One of these
# comes up, a line at a time, and it is all the box says for the rest of the
# wave - the HEADs stop being the thing worth narrating.
MONOLOGUE = (
    (
        "* Despite everything, it's still you.",
        "* Knees going. Still standing.",
    ),
    (
        "* The heart is cracked right through.",
        "* It is still the only one you have.",
        "* So hold it. The wave ends.",
    ),
    (
        "* You are running on fumes and spite.",
        "* Mostly spite.",
    ),
    (
        "* Somewhere someone is still sure you make it.",
        "* That someone is you.",
        "* Don't make a liar of yourself.",
    ),
    (
        "* One more. You only have to not be hit.",
        "* You have been doing it all along.",
    ),
)

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

    def __init__(self, spot, drift, size, tell=0.0, pellet=False, blue=False):
        self.spot = pygame.Vector2(spot)
        self.drift = pygame.Vector2(drift)
        self.size = size
        self.tell = tell
        self.pellet = pellet
        self.blue = blue  # a blue one only bites what moves

    @property
    def live(self):
        """False while it is still only a warning, and cannot hit anything."""
        return self.tell <= 0

    stays = False  # a bone travels, so it is always on its way off the board

    @property
    def gone(self):
        """A bone is spent by leaving the screen and by nothing else."""
        return False

    def hurts(self, moving):
        """Whether it can take HP off as things stand."""
        return self.live and (not self.blue or moving)

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
        color = BLUE if self.blue else BONE
        if self.pellet:
            pygame.draw.circle(surface, color, self.spot, self.size[0] / 2)
            return
        pygame.draw.rect(surface, color, rect)
        # the knobs on the ends, so a bone reads as a bone and not as a bar
        knob = min(self.size) * 0.8
        if self.size[1] >= self.size[0]:
            ends = ((rect.centerx, rect.top), (rect.centerx, rect.bottom))
        else:
            ends = ((rect.left, rect.centery), (rect.right, rect.centery))
        for end in ends:
            pygame.draw.circle(surface, color, end, knob)


class Blaster:
    """A skull that lines up on a row or a column, charges, and fires.

    It is the one thing in here that does not travel. It appears pointed at
    where you are standing, holds there long enough to be got out of the way
    of, and then the beam is on across the whole box for a beat. The charge
    is the warning and the only one there is.
    """

    stays = True  # it does not travel, so it is still there in a moment

    def __init__(self, box, across, where, from_low=True, tell=BLASTER_TELL):
        self.box = pygame.Rect(box)
        self.across = across    # True for a beam along a row, False down a column
        self.where = where      # the row, or the column, it is lined up on
        self.from_low = from_low  # which end of that line the skull sits at
        self.tell = tell
        self.burn = BEAM_TIME
        self.blue = False

    @property
    def live(self):
        return self.tell <= 0 and self.burn > 0

    @property
    def gone(self):
        """Spent once the beam has burnt out; it has nowhere to travel to."""
        return self.burn <= 0

    @property
    def thickness(self):
        """How deep the beam is right now - it thins out as it dies."""
        if self.tell > 0:
            return BEAM_WIDTH
        return BEAM_WIDTH * min(1.0, self.burn / BEAM_TIME * 2.2)

    def span(self):
        """The two ends of the beam: the muzzle, and just past the far side."""
        if self.across:
            near = self.muzzle()[0]
            far = self.box.right + BEAM_OVER if self.from_low else self.box.left - BEAM_OVER
        else:
            near = self.muzzle()[1]
            far = self.box.bottom + BEAM_OVER if self.from_low else self.box.top - BEAM_OVER
        return (min(near, far), max(near, far))

    def along(self, deep):
        """The beam's rectangle at `deep` across: drawn and hit off this one."""
        start, end = self.span()
        if self.across:
            return pygame.Rect(
                round(start), round(self.where - deep / 2), round(end - start), round(deep)
            )
        return pygame.Rect(
            round(self.where - deep / 2), round(start), round(deep), round(end - start)
        )

    @property
    def rect(self):
        return self.along(max(2, self.thickness))

    def hurts(self, moving):
        return self.live

    def muzzle(self):
        """Where the head sits: just outside the box, on the end it fires from."""
        if self.across:
            x = self.box.left - SKULL_GAP if self.from_low else self.box.right + SKULL_GAP
            return (x, self.where)
        y = self.box.top - SKULL_GAP if self.from_low else self.box.bottom + SKULL_GAP
        return (self.where, y)

    def advance(self, dt):
        if self.tell > 0:
            self.tell -= dt
            return
        self.burn -= dt

    def skull(self):
        """The head, drawn pointing right and then turned to face its beam."""
        face = pygame.Surface(SKULL, pygame.SRCALPHA)
        box = pygame.Rect((0, 0), SKULL)
        cranium = pygame.Rect(0, 0, SKULL[0] * 0.62, SKULL[1])
        pygame.draw.rect(face, BONE, cranium, border_radius=7)
        # the snout, tapering out towards whatever it is pointed at
        pygame.draw.polygon(
            face,
            BONE,
            [
                (cranium.right - 4, box.top + 5),
                (box.right, box.centery - 7),
                (box.right, box.centery + 7),
                (cranium.right - 4, box.bottom - 5),
            ],
        )
        for eye in (box.centery - 8, box.centery + 8):
            pygame.draw.rect(face, BACKDROP, (6, eye - 4, 11, 8), border_radius=2)
        pygame.draw.rect(face, BACKDROP, (cranium.right - 3, box.centery - 5, 4, 10))
        turn = 0 if self.from_low else 180
        if not self.across:
            turn = -90 if self.from_low else 90
        return pygame.transform.rotate(face, turn)

    def draw(self, surface):
        """The beam first and the head over it, so the head is never inside it."""
        head = self.skull()
        if self.tell > 0:
            # the line it is lined up on, drawn the way every other warning in
            # here is drawn: hollow, and in the grey that means not yet
            pygame.draw.rect(surface, TELL_LINE, self.along(2))
            # and the head comes in small and settles at full size, so the
            # charge is a thing arriving rather than a thing sitting there
            grown = SKULL_RUSH + (1 - SKULL_RUSH) * (1 - self.tell / BLASTER_TELL)
            head = pygame.transform.rotozoom(head, 0, grown)
        else:
            beam = self.rect
            pygame.draw.rect(surface, BEAM_EDGE, beam)
            core = (
                beam.inflate(0, -round(beam.height * 0.45))
                if self.across
                else beam.inflate(-round(beam.width * 0.45), 0)
            )
            pygame.draw.rect(surface, BEAM_CORE, core)
        surface.blit(head, head.get_rect(center=self.muzzle()))


class Determination:
    """The dodging box. `begin` a wave, advance it every frame, read `done`.

    Unlike the gun this is not a one-shot: DETERMINATION can be picked
    every turn, so every wave is built fresh and the old one thrown away.
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
        self.moving = False  # whether the arrows are being held this frame
        self.grace = 0.0
        self.wait = TELL + 0.3  # the first volley does not arrive instantly
        self.last = None        # the pattern that came up last, so none repeats
        self.murmur = None      # the low-HP lines, once the HP has got that low
        self.murmured = 0.0     # and how long they have been up, in seconds
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
        """True while DETERMINATION owns the whole screen.

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
        self.listen(dt)

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

    def listen(self, dt):
        """Keep the low-HP lines on their own clock, which the phases don't reset.

        They start the moment the HP is low enough - picked once, and kept for
        the rest of the wave however the wave goes.
        """
        if self.phase not in (OPENING, DODGING) or not self.player.alive:
            return
        if self.player.health > LOW_HP:
            return
        if self.murmur is None:
            self.murmur = self.rolls.choice(MONOLOGUE)
        self.murmured += dt

    def drive(self, keys, dt):
        """The arrows move the heart, and the box is as far as it goes."""
        move = pygame.Vector2(
            held(keys, RIGHT) - held(keys, LEFT),
            held(keys, DOWN) - held(keys, UP),
        )
        # the blue bones read the keys rather than the position, so pinned
        # against the edge of the box with an arrow down still counts
        self.moving = bool(move.length_squared())
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

        # what the wave is allowed to throw yet: it opens on bones and turns
        # into skulls and walls, so the first volley is never the worst one
        patterns = [self.rain, self.sweep, self.closing]
        if run > HARDER_AT:
            patterns += [self.wall, self.blasters]
        # a blue wall asks you to stand still, and everything in the air when
        # it goes up will have travelled off the board before it arrives -
        # everything except a skull, which is still sitting there waiting to
        # fire. So no blue wall while one of those is up.
        if run > HARDEST_AT and not any(shot.stays for shot in self.shots):
            patterns.append(self.blue_wall)
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
            if shot.gone or not reach.colliderect(shot.rect):
                continue  # spent, or gone past the screen; nobody's problem now
            live.append(shot)
            if shot.hurts(self.moving) and not self.grace and shot.rect.colliderect(self.hitbox()):
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

    def wall(self):
        """A rank of bone crossing the box with one slot in it.

        It fills the box top to bottom but for the slot, so there is no
        dodging it on the spot: you line the heart up with the gap and ride
        it across. It comes in from outside the box, where it is still drawn,
        which is the only warning it gives and all the warning it needs.
        """
        box = self.box()
        from_left = self.rolls.random() < 0.5
        gap = self.rolls.uniform(box.top + WALL_GAP, box.bottom - WALL_GAP)
        start = box.left - WALL_WIDTH * 3 if from_left else box.right + WALL_WIDTH * 3
        speed = WALL_SPEED if from_left else -WALL_SPEED
        # a wall is a thing you ride across rather than step around, so it is
        # given most of its crossing to itself before the next volley lands
        self.wait = max(self.wait, box.width / WALL_SPEED * WALL_CLEAR)
        bones = []
        for top, bottom in (
            (box.top, gap - WALL_GAP / 2),
            (gap + WALL_GAP / 2, box.bottom),
        ):
            bones.append(
                Shot(
                    (start, (top + bottom) / 2),
                    (speed, 0),
                    (WALL_WIDTH, bottom - top),
                )
            )
        return bones

    def blue_wall(self):
        """The same wall with no slot in it at all, in blue.

        There is nowhere to put the heart, so the answer is not to put it
        anywhere: a blue bone only bites what moves, and the wall passes
        straight through a heart that is holding still.
        """
        box = self.box()
        from_left = self.rolls.random() < 0.5
        lead = box.width * BLUE_LEAD
        start = box.left - lead if from_left else box.right + lead
        speed = BLUE_WALL_SPEED if from_left else -BLUE_WALL_SPEED
        # it starts well outside the box and nothing else comes while it is
        # on its way or crossing: a wall you have to stand still for is only
        # fair if standing still is enough, which means the board in front of
        # it has to be empty by the time it arrives
        self.wait = max(self.wait, (lead + box.width) / BLUE_WALL_SPEED + BLUE_CLEAR)
        return [
            Shot(
                (start, box.centery),
                (speed, 0),
                (BLUE_WALL_WIDTH, box.height),
                blue=True,
            )
        ]

    def blasters(self):
        """One or two skulls, the first of them aimed at where you are now.

        The aim is taken when they appear and they do not follow you, so the
        charge is long enough to simply walk out of - which is the pattern:
        you are being asked to stop standing still, having just been asked to
        stand still.
        """
        box = self.box()
        shots = []
        # the charge is the dodge: nothing else arrives during it
        self.wait = max(self.wait, BLASTER_TELL + BLASTER_CLEAR)
        for i in range(self.rolls.randint(1, 2)):
            across = self.rolls.random() < 0.5
            if i == 0:
                where = self.heart.y if across else self.heart.x
            elif across:
                where = self.rolls.uniform(box.top + BEAM_WIDTH, box.bottom - BEAM_WIDTH)
            else:
                where = self.rolls.uniform(box.left + BEAM_WIDTH, box.right - BEAM_WIDTH)
            shots.append(
                Blaster(
                    box,
                    across,
                    round(where),
                    from_low=self.rolls.random() < 0.5,
                    tell=BLASTER_TELL + 0.12 * i,  # the second one lands behind the first
                )
            )
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
        """The heart, drawn where it is - the same one the text box picks with."""
        if self.grace and int(self.grace * FLICKER) % 2:
            return  # the flicker after a hit: it blinks out and back
        textbox.draw_soul(surface, spot, size, color)

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

    @property
    def blue_up(self):
        """True while something that only bites movement is on the board."""
        return any(shot.blue and shot.live for shot in self.shots)

    def draw_lines(self, surface):
        """What the box has to say, in the asterisks it says everything in."""
        font = assets.font(24)
        if self.blue_up:
            # this one jumps the queue, low HP or not: being hit by a rule
            # nobody told you about is the only unfair thing in here
            surface.blit(
                font.render("* Blue bones only bite what moves.", True, BLUE), (40, 36)
            )
            return
        if self.murmur is not None:
            self.draw_murmur(surface, font)
            return
        said = ["* The HEADs answer."]
        if self.phase == OPENING or self.beat < 2.4:
            said.append("* Arrows move the heart. Nothing else moves.")
        for i, line in enumerate(said):
            surface.blit(font.render(line, True, TEXT), (40, 36 + i * 28))

    def draw_murmur(self, surface, font):
        """The low lines, arriving one by one and breathing like something alive."""
        breath = MURMUR_FLOOR + (1 - MURMUR_FLOOR) * (
            0.5 + 0.5 * math.sin(self.murmured * MURMUR_PULSE)
        )
        for i, line in enumerate(self.murmur):
            since = self.murmured - i * MURMUR_LINE
            if since <= 0:
                break  # it has not got this far yet
            arrived = min(1.0, since / MURMUR_FADE)
            text = font.render(line, True, DETERMINED)
            text.set_alpha(round(255 * arrived * breath))
            surface.blit(text, (40, 36 + i * 28))

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
