"""Base class shared by everything that lives, fights and gets drawn."""

import pygame


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

    @property
    def alive(self):
        return self.health > 0

    def take_damage(self, amount):
        if self.guarding:
            amount = max(1, amount // 2)
        self.health = max(0, self.health - amount)
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
        target.take_damage(self.attack_damage)
        return target.health

    def update(self, dt):
        pass

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.pos, self.radius)

    def __repr__(self):
        return (
            f"{self.name}(hp={self.health}/{self.max_health}, "
            f"mp={self.mana}/{self.max_mana}, atk={self.attack_damage})"
        )
