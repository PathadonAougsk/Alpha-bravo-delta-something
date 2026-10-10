"""Enemies: they hold a spot on the field and wait their turn."""

import math
import random

import pygame

import assets
from entity import Entity, approach
from stats import BASE, ENEMY, roll

ENEMY_NAME = "HEAD"
SIZE = 1.2           # 20% bigger than the plain health-derived size
SPRITE_SCALE = 3.4   # sprite height as a multiple of the enemy's radius
MAX_RADIUS = 150     # a huge conflict hunk still has to fit on the field

HOVER_PIXELS = 5.0   # how far it rides up and down on the spot
HOVER_SPEED = 1.6    # radians a second
SHAKE_PIXELS = 7.0   # how hard it shudders the moment a hit lands
SHAKE_SPEED = 46.0   # and how fast that shudder rattles
DEATH_FADE = 0.55    # seconds a beaten HEAD takes to leave the field
DEATH_SINK = 18      # pixels it slumps on the way out

# A HEAD whose attack is turned aside by a guard lands on its side until it
# has spent a turn getting back up.
TOPPLE_TIME = 0.22    # seconds the fall over (and the climb back) takes
TOPPLE_ANGLE = 90     # degrees it ends up rotated once it is down
TOPPLE_TINT = (55, 95, 210)   # the blue it is washed towards while it is down
TOPPLE_WASH = 0.55    # how far towards that blue, at full topple

# The cursor that picks which HEAD the swing lands on.
CURSOR_COLOR = (255, 148, 38)  # orange, so it reads against the blues and reds
CURSOR_ALPHA = 200             # see-through, but still orange over a green field
CURSOR_EDGE = (255, 228, 180)  # a paler rim around the diamond
CURSOR_SIZE = 17               # half-height of the diamond, in pixels
CURSOR_GAP = 10                # how far it floats above the health bar
CURSOR_BOB_PIXELS = 4.0        # it nods up and down so the eye catches it
CURSOR_BOB_SPEED = 5.4         # radians a second


class Enemy(Entity):
    def __init__(self, pos, name=ENEMY_NAME, radius=None, color=None, sprite=None, **stats):
        health = stats.get("health", 40)
        # every HEAD is drawn from the pool; they are all scaled to the same
        # height, so a tall one stands where a round one hovers
        self.sprite = sprite or random.choice(assets.ENEMIES)
        super().__init__(
            pos,
            radius=(
                radius
                if radius is not None
                else min(MAX_RADIUS, round((16 + health * 0.25) * SIZE))
            ),
            color=color or (190, 80, 90),
            name=name,
            **stats,
        )
        self._font = None
        self.phase = random.uniform(0, math.tau)  # so a row of them hovers out of step
        self.death = 0.0                          # counts up once it is beaten
        self.recovering = False  # its attack failed; its next turn is spent getting up
        self.topple = 0.0        # 0 upright, 1 flat on its side

    @classmethod
    def spawn(cls, pos, name=ENEMY_NAME, base=BASE):
        """One enemy, rolled around the baseline."""
        return cls(
            pos,
            name=name,
            color=(
                random.randint(90, 220),
                random.randint(60, 140),
                random.randint(110, 230),
            ),
            **roll(ENEMY, base),
        )

    @classmethod
    def formation(cls, count, width, height, base=BASE):
        """Lay `count` enemies out in a row across the upper half of the field."""
        if count <= 0:
            return []
        # the field is the right-hand side; the player stands in the left foreground
        left, right = width * 0.38, width * 0.9
        step = (right - left) / max(1, count - 1) if count > 1 else 0
        return [
            cls.spawn(
                (left + step * i if count > 1 else (left + right) / 2, height * 0.56),
                name=ENEMY_NAME if count == 1 else f"{ENEMY_NAME}~{i + 1}",
                base=base,
            )
            for i in range(count)
        ]

    # ------------------------------------------------------------- animation

    def update(self, dt):
        super().update(dt)
        if not self.alive:
            self.death += dt
            return  # a HEAD beaten on its side stays on its side as it fades
        # it tips over the moment the guard turns its attack aside, and rights
        # itself over the turn it spends recovering
        self.topple = approach(
            self.topple, 1.0 if self.recovering else 0.0, dt / TOPPLE_TIME
        )

    def fail_attack(self):
        """Its swing came off a guard: it goes down, and loses its next turn."""
        self.recovering = True

    def recover(self):
        """Spend the turn getting back on its feet."""
        self.recovering = False

    @property
    def fading(self):
        """0 the moment it is beaten, 1 once it has gone."""
        return min(1.0, self.death / DEATH_FADE)

    @property
    def gone(self):
        return not self.alive and self.death >= DEATH_FADE

    @property
    def drift(self):
        """Hovering, plus a shudder while a hit is still landing."""
        hover = math.sin(self.elapsed * HOVER_SPEED + self.phase) * HOVER_PIXELS
        shake = (
            math.sin(self.hit_timer * SHAKE_SPEED) * SHAKE_PIXELS * self.hit_flash
            if self.hit_timer > 0
            else 0.0
        )
        return pygame.Vector2(shake, hover + self.fading * DEATH_SINK) + self.lunge

    # --------------------------------------------------------------- drawing

    def draw(self, surface, targeted=False):
        if self.gone:
            return
        here = self.pos + self.drift
        sprite = assets.by_height(self.sprite, round(self.radius * SPRITE_SCALE))

        if sprite is not None:
            sprite = assets.flashed(sprite, self.hit_flash)
            sprite = assets.tinted(sprite, TOPPLE_TINT, TOPPLE_WASH * self.topple)
            # the bar and the name hang off the upright footprint, so they stay
            # put while the body itself spins onto its side
            rect = sprite.get_rect(center=(here.x, here.y))
            if self.topple > 0:
                sprite = pygame.transform.rotate(sprite, -TOPPLE_ANGLE * self.topple)
            if not self.alive:
                sprite = sprite.copy()
                sprite.set_alpha(round(255 * (1 - self.fading)))
            surface.blit(sprite, sprite.get_rect(center=(here.x, here.y)))
        else:
            r = self.radius
            color = self.color
            if self.topple > 0:
                wash = TOPPLE_WASH * self.topple
                color = tuple(
                    round(c * (1 - wash) + t * wash) for c, t in zip(color, TOPPLE_TINT)
                )
            points = [
                (here.x, here.y - r),
                (here.x + r, here.y),
                (here.x, here.y + r),
                (here.x - r, here.y),
            ]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, (20, 20, 30), points, 2)
            if targeted:
                pygame.draw.polygon(surface, (255, 235, 120), points, 3)
            rect = pygame.Rect(0, 0, r * 2, r * 2)
            rect.center = (here.x, here.y)

        if self.alive:  # a beaten HEAD drops its furniture and just fades
            self.draw_health_bar(surface, rect)
            self.draw_name(surface, rect, targeted)
            if targeted:
                self.draw_cursor(surface, rect)
        # the number stays up through the death fade: the blow that finished
        # it off is the one worth reading
        self.draw_damage(surface, (rect.centerx, rect.centery - 10))

    def draw_cursor(self, surface, rect):
        """The orange diamond that sits over whoever the swing is aimed at."""
        bob = math.sin(self.elapsed * CURSOR_BOB_SPEED) * CURSOR_BOB_PIXELS
        centre = (CURSOR_SIZE + 2, CURSOR_SIZE + 2)
        size = CURSOR_SIZE * 2 + 4
        diamond = pygame.Surface((size, size), pygame.SRCALPHA)
        points = [
            (centre[0], centre[1] - CURSOR_SIZE),
            (centre[0] + CURSOR_SIZE, centre[1]),
            (centre[0], centre[1] + CURSOR_SIZE),
            (centre[0] - CURSOR_SIZE, centre[1]),
        ]
        pygame.draw.polygon(diamond, (*CURSOR_COLOR, CURSOR_ALPHA), points)
        pygame.draw.polygon(diamond, (*CURSOR_EDGE, CURSOR_ALPHA), points, 2)
        surface.blit(
            diamond,
            diamond.get_rect(
                center=(rect.centerx, rect.top - 12 - CURSOR_GAP - CURSOR_SIZE + bob)
            ),
        )

    def draw_name(self, surface, rect, targeted=False):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 20, bold=True)
        label = self._font.render(
            self.name, True, (255, 235, 120) if targeted else (225, 228, 245)
        )
        shadow = self._font.render(self.name, True, (12, 14, 24))
        spot = label.get_rect(midtop=(rect.centerx, rect.bottom + 4))
        surface.blit(shadow, spot.move(1, 1))
        surface.blit(label, spot)

    def draw_health_bar(self, surface, rect):
        width, height = rect.width, 6
        x, y = rect.centerx - width / 2, rect.top - 12
        pygame.draw.rect(surface, (20, 22, 32), (x - 1, y - 1, width + 2, height + 2))
        pygame.draw.rect(surface, (60, 62, 78), (x, y, width, height))
        # the pale sliver is the damage the bar has yet to catch up on
        pygame.draw.rect(
            surface,
            (240, 170, 180),
            (x, y, width * self.shown_health / self.max_health, height),
        )
        pygame.draw.rect(
            surface, (220, 90, 110), (x, y, width * self.health / self.max_health, height)
        )
