"""The entity the keyboard drives."""

import pygame

from entity import Entity
from stats import BASE, PLAYER, roll

PLAYER_SPEED = 320  # pixels per second
PLAYER_COLOR = (240, 240, 250)
PLAYER_SPREAD = 0.08  # the hero varies less than the monsters do
PLAYER_NAME = "Feature Branch"


class Player(Entity):
    def __init__(self, pos, base=BASE, speed=PLAYER_SPEED, name=PLAYER_NAME, **overrides):
        stats = roll(PLAYER, base, PLAYER_SPREAD)
        stats.update(overrides)
        super().__init__(
            pos,
            radius=12,
            color=PLAYER_COLOR,
            name=name,
            **stats,
        )
        self.speed = speed

    def handle_input(self, keys, dt):
        move = pygame.Vector2(
            keys[pygame.K_RIGHT] - keys[pygame.K_LEFT],
            keys[pygame.K_DOWN] - keys[pygame.K_UP],
        )
        if move.length_squared():
            self.pos += move.normalize() * self.speed * dt

    def clamp_to(self, width, height):
        self.pos.x = max(self.radius, min(width - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(height - self.radius, self.pos.y))
