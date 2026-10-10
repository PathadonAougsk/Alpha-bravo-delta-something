"""The entity the keyboard drives."""

import math

import pygame

import assets
from entity import Entity
from stats import BASE, PLAYER, roll

PLAYER_SPEED = 320  # pixels per second
PLAYER_COLOR = (240, 240, 250)
PLAYER_SPREAD = 0.08  # the hero varies less than the monsters do
PLAYER_NAME = "Feature Branch"
SPRITE_HEIGHT = 320  # how tall Makoto stands in the foreground

BOB_PIXELS = 3.0  # how far he rises and settles while standing there
BOB_SPEED = 1.9   # radians a second

# The sword rides in the hand on the enemies' side of the sprite, and holds
# still. Both points are fractions of their own image, so they survive any
# rescaling of either one.
SWORD_HEIGHT = 86            # how long the blade looks in that grip
SWORD_HAND = (0.857, 0.536)  # the hand, within the character sprite
SWORD_HILT = (0.459, 0.795)  # where the hand closes, within the sword sprite


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

    @property
    def stance(self):
        """Where he actually stands this frame: breathing, plus any lunge."""
        bob = math.sin(self.elapsed * BOB_SPEED) * BOB_PIXELS
        return pygame.Vector2(0, bob) + self.lunge

    def draw(self, surface):
        sprite = assets.by_height(assets.PLAYER, SPRITE_HEIGHT)
        if sprite is None:
            super().draw(surface)
            return
        flash = self.hit_flash
        feet = pygame.Vector2(self.pos.x, self.pos.y + self.radius) + self.stance
        sprite = assets.flashed(sprite, flash)
        rect = sprite.get_rect(midbottom=feet)
        surface.blit(sprite, rect)
        self.draw_sword(surface, rect, flash)
        self.draw_damage(surface, (rect.centerx, rect.centery))

    def draw_sword(self, surface, rect, flash=0.0):
        """The sword, held steady in the hand the sprite points at the enemy."""
        sword = assets.by_height(assets.SWORD, SWORD_HEIGHT)
        if sword is None:
            return
        hand = (
            rect.left + rect.width * SWORD_HAND[0],
            rect.top + rect.height * SWORD_HAND[1],
        )
        sword = assets.flashed(sword, flash)
        surface.blit(
            sword,
            (
                hand[0] - sword.get_width() * SWORD_HILT[0],
                hand[1] - sword.get_height() * SWORD_HILT[1],
            ),
        )

    def clamp_to(self, width, height):
        self.pos.x = max(self.radius, min(width - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(height - self.radius, self.pos.y))
