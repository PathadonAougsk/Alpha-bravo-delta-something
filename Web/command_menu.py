"""The JRPG command ring: ATTACK, GUARD, ITEM.

A blue wheel with a lettered button per direction and the command name
spelled out beside it, in the Persona-style command block.
"""

import pygame

ATTACK = "attack"
GUARD = "guard"
ITEM = "item"

RING_COLOR = (42, 96, 232)
RING_EDGE = (150, 200, 255)
BUTTON_FILL = (28, 64, 170)
BUTTON_EDGE = (235, 242, 255)
TEXT_COLOR = (255, 255, 255)
TEXT_SHADOW = (10, 18, 50)
DIM = (150, 165, 200)


class Command:
    """One slot on the wheel: a direction, a face button, a label."""

    def __init__(self, action, label, button, direction, align):
        self.action = action
        self.label = label
        self.button = button          # letter drawn in the little circle
        self.direction = pygame.Vector2(direction)
        self.align = align            # which side of the button the label sits on


class CommandMenu:
    RADIUS = 72
    BUTTON_RADIUS = 15
    BUTTON_OFFSET = 34

    def __init__(self):
        self.commands = [
            Command(ATTACK, "ATTACK", "A", (1, 0), "right"),
            Command(GUARD, "GUARD", "B", (0, 1), "right"),
            Command(ITEM, "ITEM", "Y", (-1, 0), "left"),
        ]
        self.index = 0
        self._font = None
        self._button_font = None

    # ------------------------------------------------------------------ input

    def handle_event(self, event):
        """Feed it pygame events; returns an action string once confirmed."""
        if event.type != pygame.KEYDOWN:
            return None

        for i, command in enumerate(self.commands):
            if self._key_matches(event.key, command.direction):
                self.index = i
                return None

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return self.selected.action
        return None

    @staticmethod
    def _key_matches(key, direction):
        if direction.x > 0:
            return key == pygame.K_RIGHT
        if direction.x < 0:
            return key == pygame.K_LEFT
        if direction.y > 0:
            return key == pygame.K_DOWN
        return key == pygame.K_UP

    @property
    def selected(self):
        return self.commands[self.index]

    # ----------------------------------------------------------------- drawing

    def draw(self, surface, center):
        if self._font is None:
            self._font = pygame.font.SysFont(None, 42, bold=True, italic=True)
            self._button_font = pygame.font.SysFont(None, 24, bold=True)

        center = pygame.Vector2(center)
        self._draw_ring(surface, center)

        for i, command in enumerate(self.commands):
            selected = i == self.index
            button_pos = center + command.direction * self.BUTTON_OFFSET
            pygame.draw.circle(surface, BUTTON_FILL, button_pos, self.BUTTON_RADIUS)
            pygame.draw.circle(
                surface,
                BUTTON_EDGE if selected else DIM,
                button_pos,
                self.BUTTON_RADIUS,
                3 if selected else 2,
            )
            glyph = self._button_font.render(command.button, True, BUTTON_EDGE)
            surface.blit(glyph, glyph.get_rect(center=button_pos))

            self._draw_label(surface, command, button_pos, selected)

    def _draw_ring(self, surface, center):
        size = self.RADIUS * 2 + 8
        ring = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(ring, (*RING_COLOR, 205), (size // 2, size // 2), self.RADIUS)
        pygame.draw.circle(ring, (*RING_EDGE, 120), (size // 2, size // 2), self.RADIUS, 3)
        surface.blit(ring, ring.get_rect(center=center))

    def _draw_label(self, surface, command, button_pos, selected):
        color = TEXT_COLOR if selected else DIM
        text = self._font.render(command.label, True, color)
        rect = text.get_rect()
        gap = self.BUTTON_RADIUS + 10
        if command.align == "right":
            rect.midleft = (button_pos.x + gap, button_pos.y + 4)
        else:
            rect.midright = (button_pos.x - gap, button_pos.y + 4)

        # cheap outline so the text stays readable over the battlefield
        shadow = self._font.render(command.label, True, TEXT_SHADOW)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2)):
            surface.blit(shadow, rect.move(dx, dy))
        surface.blit(text, rect)
