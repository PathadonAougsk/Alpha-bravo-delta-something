"""Base class shared by everything that lives, fights and gets drawn."""

import math

import pygame

import assets

HIT_FLASH = 0.32    # seconds an entity keeps flashing after it is hit
LUNGE_TIME = 0.34   # seconds a lunge takes, there and back again
LUNGE_REACH = 34    # pixels it covers at the furthest point of that lunge
BAR_CATCHUP = 1.5   # how fast a bar chases its number, in full bars a second

# The number that pops off whoever just took a hit.
DAMAGE_TIME = 0.95        # seconds it stays up
DAMAGE_RISE = 40          # pixels it floats on the way out
DAMAGE_SIZE = 38          # how big it is drawn
DAMAGE_FADE = 0.45        # the last fraction of its life is spent fading
DAMAGE_COLOR = (255, 226, 120)
DAMAGE_SHADOW = (26, 14, 10)


def approach(shown, target, step):
    """Move `shown` at most `step` towards `target`."""
    if shown < target:
        return min(target, shown + step)
    return max(target, shown - step)


class Entity:
    """Anything with health, mana and attack damage."""

    def __init__(
        self,
        pos,
        health=100,
        mana=50,
        attack_damage=10,
        radius=12,
        color=(240, 240, 250),
        name=None,
    ):
        self.pos = pygame.Vector2(pos)
        self.name = name or type(self).__name__
        self.max_health = health
        self.health = health
        self.max_mana = mana
        self.mana = mana
        self.attack_damage = attack_damage
        self.radius = radius
        self.color = color
        self.guarding = False

        # animation state: where the body is and what it is doing, as opposed
        # to the numbers above, which are what the battle actually runs on
        self.elapsed = 0.0       # drives the idling
        self.hit_timer = 0.0     # counts down after taking a hit
        self.lunge_timer = 0.0   # counts down while swinging at someone
        self.lunge_direction = pygame.Vector2()
        self.shown_health = float(health)  # what the bars are displaying...
        self.shown_mana = float(mana)      # ...on their way to the real number
        self.damage = None        # the last number taken off this entity
        self.damage_timer = 0.0   # counts down while that number is up

    @property
    def alive(self):
        return self.health > 0

    # ------------------------------------------------------------- animation

    def update(self, dt):
        self.elapsed += dt
        self.hit_timer = max(0.0, self.hit_timer - dt)
        self.lunge_timer = max(0.0, self.lunge_timer - dt)
        self.damage_timer = max(0.0, self.damage_timer - dt)
        self.shown_health = approach(
            self.shown_health, self.health, self.max_health * BAR_CATCHUP * dt
        )
        self.shown_mana = approach(
            self.shown_mana, self.mana, self.max_mana * BAR_CATCHUP * dt
        )

    @property
    def hit_flash(self):
        """1 the instant a hit lands, fading to 0."""
        return self.hit_timer / HIT_FLASH

    @property
    def lunge(self):
        """How far the body has stepped off its mark, mid-swing."""
        if self.lunge_timer <= 0:
            return pygame.Vector2()
        done = 1 - self.lunge_timer / LUNGE_TIME
        return self.lunge_direction * math.sin(math.pi * done) * LUNGE_REACH

    def lunge_at(self, target):
        """Start the step towards whoever is about to be hit."""
        self.lunge_timer = LUNGE_TIME
        gap = pygame.Vector2(target.pos) - self.pos
        self.lunge_direction = gap.normalize() if gap.length_squared() else pygame.Vector2()

    # ---------------------------------------------------------------- combat

    def take_damage(self, amount):
        if self.guarding:
            amount = max(1, amount // 2)
        self.health = max(0, self.health - amount)
        self.hit_timer = HIT_FLASH
        # what actually came off, guard and all, is what the number shows
        self.damage, self.damage_timer = amount, DAMAGE_TIME
        return self.health

    def guard(self):
        """Halve incoming damage until this entity acts again."""
        self.guarding = True

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)
        return self.health

    def spend_mana(self, amount):
        """Spend mana if there is enough of it; True when it was paid."""
        if self.mana < amount:
            return False
        self.mana -= amount
        return True

    def restore_mana(self, amount):
        self.mana = min(self.max_mana, self.mana + amount)
        return self.mana

    def attack(self, target):
        """Hit another entity for this entity's attack damage."""
        self.lunge_at(target)
        target.take_damage(self.attack_damage)
        return target.health

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.pos, self.radius)

    def draw_damage(self, surface, anchor):
        """The number that came off this entity, floating up and fading out."""
        if self.damage is None or self.damage_timer <= 0:
            return
        done = 1 - self.damage_timer / DAMAGE_TIME
        text = assets.font(DAMAGE_SIZE).render(str(self.damage), True, DAMAGE_COLOR)
        shadow = assets.font(DAMAGE_SIZE).render(str(self.damage), True, DAMAGE_SHADOW)
        # a quick pop out of the body, then a slow drift: ease_out on the rise
        rise = DAMAGE_RISE * (1 - (1 - done) ** 2)
        spot = text.get_rect(center=(anchor[0], anchor[1] - rise))
        if done > 1 - DAMAGE_FADE:
            alpha = round(255 * (1 - done) / DAMAGE_FADE)
            text, shadow = text.copy(), shadow.copy()
            text.set_alpha(alpha)
            shadow.set_alpha(alpha)
        for step in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surface.blit(shadow, spot.move(step))
        surface.blit(text, spot)

    def __repr__(self):
        return (
            f"{self.name}(hp={self.health}/{self.max_health}, "
            f"mp={self.mana}/{self.max_mana}, atk={self.attack_damage})"
        )
