"""Enemies: they hold a spot on the field and wait their turn."""

import math
import random

import pygame

import assets
from entity import Entity
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


class Enemy(Entity):
    def __init__(self, pos, name=ENEMY_NAME, radius=None, color=None, **stats):
        health = stats.get("health", 40)
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
        sprite = assets.by_height(assets.ENEMY, round(self.radius * SPRITE_SCALE))

        if sprite is not None:
            sprite = assets.flashed(sprite, self.hit_flash)
            if not self.alive:
                sprite = sprite.copy()
                sprite.set_alpha(round(255 * (1 - self.fading)))
            rect = sprite.get_rect(center=(here.x, here.y))
            surface.blit(sprite, rect)
        else:
            r = self.radius
            points = [
                (here.x, here.y - r),
                (here.x + r, here.y),
                (here.x, here.y + r),
                (here.x - r, here.y),
            ]
            pygame.draw.polygon(surface, self.color, points)
            pygame.draw.polygon(surface, (20, 20, 30), points, 2)
            if targeted:
                pygame.draw.polygon(surface, (255, 235, 120), points, 3)
            rect = pygame.Rect(0, 0, r * 2, r * 2)
            rect.center = (here.x, here.y)

        if self.alive:  # a beaten HEAD drops its furniture and just fades
            self.draw_health_bar(surface, rect)
            self.draw_name(surface, rect, targeted)

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
