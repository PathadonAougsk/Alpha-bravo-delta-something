"""Enemies: they hold a spot on the field and wait their turn."""

import random

import pygame

from entity import Entity
from stats import BASE, ENEMY, roll

ENEMY_NAME = "HEAD"


class Enemy(Entity):
    def __init__(self, pos, name=ENEMY_NAME, radius=None, color=None, **stats):
        health = stats.get("health", 40)
        super().__init__(
            pos,
            radius=radius if radius is not None else round(16 + health * 0.25),
            color=color or (190, 80, 90),
            name=name,
            **stats,
        )
        self._font = None

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
        step = width / (count + 1)
        return [
            cls.spawn(
                (step * (i + 1), height * 0.32),
                name=ENEMY_NAME if count == 1 else f"{ENEMY_NAME}~{i + 1}",
                base=base,
            )
            for i in range(count)
        ]

    def draw(self, surface, targeted=False):
        r = self.radius
        points = [
            (self.pos.x, self.pos.y - r),
            (self.pos.x + r, self.pos.y),
            (self.pos.x, self.pos.y + r),
            (self.pos.x - r, self.pos.y),
        ]
        pygame.draw.polygon(surface, self.color, points)
        pygame.draw.polygon(surface, (20, 20, 30), points, 2)
        if targeted:
            pygame.draw.polygon(surface, (255, 235, 120), points, 3)
        self.draw_health_bar(surface)
        self.draw_name(surface, targeted)

    def draw_name(self, surface, targeted=False):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 20, bold=True)
        label = self._font.render(
            self.name, True, (255, 235, 120) if targeted else (205, 210, 230)
        )
        surface.blit(label, label.get_rect(midtop=(self.pos.x, self.pos.y + self.radius + 6)))

    def draw_health_bar(self, surface):
        width, height = self.radius * 2, 6
        x = self.pos.x - width / 2
        y = self.pos.y - self.radius - 14
        pygame.draw.rect(surface, (40, 40, 52), (x, y, width, height))
        filled = width * (self.health / self.max_health)
        pygame.draw.rect(surface, (220, 90, 110), (x, y, filled, height))
