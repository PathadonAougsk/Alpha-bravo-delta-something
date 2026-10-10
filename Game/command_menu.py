"""The JRPG command ring: ATTACK, GUARD, ITEM, MERCY.

A blue wheel with a lettered button per command and the name spelled out
beside it. The selected slot never moves: picking a command turns the whole
wheel until that command arrives there, and every label rides around with it,
tilting as it goes. Neighbours sit SPACING degrees off, so whatever is one
step away reads at that tilt, and anything far enough round the back of the
wheel has its label fade out rather than hang over the field upside down.
"""

import math

import pygame

ATTACK = "attack"
GUARD = "guard"
ITEM = "item"
MERCY = "mercy"

RING_COLOR = (42, 96, 232)
RING_EDGE = (150, 200, 255)
BUTTON_FILL = (28, 64, 170)
BUTTON_EDGE = (235, 242, 255)
TEXT_COLOR = (255, 255, 255)
TEXT_SHADOW = (10, 18, 50)
DIM = (150, 165, 200)
LOCKED_FILL = (26, 32, 52)    # a command the battle will not let you pick yet
LOCKED_EDGE = (86, 96, 124)
LOCKED_TEXT = (104, 114, 142)

PULSE_SPEED = 5.2    # radians a second, for the button that is picked
PULSE_PIXELS = 2.4   # how much bigger that button swells
BREATHE_PIXELS = 1.6  # and how much the ring behind it drifts in and out

SPACING = 45       # degrees between neighbouring commands on the wheel
FADE_FROM = 90     # degrees off the slot a label starts dropping away at...
FADE_TO = 135      # ...and where it is gone, round the back of the wheel
TURN_SPEED = 11.0  # how fast the wheel catches up with the pick, per second
NOTCHES = 12       # ticks around the rim, so the turning is visible


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
    BUTTON_OFFSET = 48  # far enough out that neighbours SPACING apart clear

    def __init__(self):
        self.commands = [
            Command(ATTACK, "ATTACK", "A", (1, 0), "right"),
            Command(GUARD, "GUARD", "B", (0, 1), "right"),
            Command(ITEM, "ITEM", "Y", (-1, 0), "left"),
            Command(MERCY, "MERCY", "X", (0, -1), "left"),
        ]
        self.index = 0
        self.elapsed = 0.0  # drives the pulsing
        self.angle = 0.0    # how far the wheel has turned, in degrees
        self._font = None
        self._button_font = None

    def update(self, dt):
        self.elapsed += dt
        # ease towards the turn that brings the pick round to the slot
        self.angle += (self.turn_to - self.angle) * min(1.0, dt * TURN_SPEED)

    @property
    def turn_to(self):
        """The wheel angle that puts the current pick in the selected slot."""
        return self.index * SPACING

    def angle_of(self, i):
        """Where command `i` sits right now; 0 is the selected slot."""
        return self.angle - i * SPACING

    @property
    def pulse(self):
        """-1 to 1, the beat the selected button swells on."""
        return math.sin(self.elapsed * PULSE_SPEED)

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

    def draw(self, surface, center, locked=()):
        """Lay the wheel out around `center`, greying out any locked action."""
        if self._font is None:
            self._font = pygame.font.SysFont(None, 42, bold=True, italic=True)
            self._button_font = pygame.font.SysFont(None, 24, bold=True)

        center = pygame.Vector2(center)
        self._draw_ring(surface, center)

        # furthest from the slot first, so the pick lands on top of the rest
        for i in sorted(range(len(self.commands)), key=lambda i: -abs(self.angle_of(i))):
            command = self.commands[i]
            angle = self.angle_of(i)
            selected = i == self.index
            shut = command.action in locked
            heading = pygame.Vector2(1, 0).rotate(angle)
            button_pos = center + heading * self.BUTTON_OFFSET
            radius = self.BUTTON_RADIUS + (self.pulse * PULSE_PIXELS if selected else 0)
            pygame.draw.circle(
                surface, LOCKED_FILL if shut else BUTTON_FILL, button_pos, radius
            )
            pygame.draw.circle(
                surface,
                LOCKED_EDGE if shut else (BUTTON_EDGE if selected else DIM),
                button_pos,
                radius,
                3 if selected else 2,
            )
            glyph = self._button_font.render(
                command.button, True, LOCKED_EDGE if shut else BUTTON_EDGE
            )
            surface.blit(glyph, glyph.get_rect(center=button_pos))

            self._draw_label(surface, center, command, heading, angle, selected, shut)

    def _draw_ring(self, surface, center):
        size = self.RADIUS * 2 + 8
        radius = self.RADIUS + self.pulse * BREATHE_PIXELS
        ring = pygame.Surface((size, size), pygame.SRCALPHA)
        middle = pygame.Vector2(size / 2, size / 2)
        pygame.draw.circle(ring, (*RING_COLOR, 205), middle, radius)
        pygame.draw.circle(ring, (*RING_EDGE, 120), middle, radius, 3)
        # ticks on the rim: without them a wheel of three reads as labels
        # swapping places rather than as something turning
        for notch in range(NOTCHES):
            out = pygame.Vector2(1, 0).rotate(self.angle + notch * (360 / NOTCHES))
            pygame.draw.line(
                ring,
                (*RING_EDGE, 90),
                middle + out * (radius - 11),
                middle + out * (radius - 3),
                2,
            )
        surface.blit(ring, ring.get_rect(center=center))

    def _draw_label(self, surface, center, command, heading, angle, selected, shut=False):
        """The name, out past its button and turned to match the wheel."""
        color = LOCKED_TEXT if shut else (TEXT_COLOR if selected else DIM)
        text = self._font.render(command.label, True, color)
        shadow = self._font.render(command.label, True, TEXT_SHADOW)

        # cheap outline so the text stays readable over the battlefield
        plate = pygame.Surface(
            (text.get_width() + 8, text.get_height() + 8), pygame.SRCALPHA
        )
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2)):
            plate.blit(shadow, (4 + dx, 4 + dy))
        plate.blit(text, (4, 4))

        turned = pygame.transform.rotate(plate, -angle)
        if not selected:
            # the further round it has gone, the fainter it reads, until the
            # far side of the wheel is carrying nothing but its button
            left = 1 - max(0.0, (abs(angle) - FADE_FROM) / (FADE_TO - FADE_FROM))
            if left <= 0:
                return
            turned.set_alpha(round(180 * left))
        # measured from the rim, not the button, so a short word like ITEM is
        # pushed as clear of the wheel as a long one
        reach = self.RADIUS + 14 + text.get_width() / 2
        surface.blit(turned, turned.get_rect(center=center + heading * reach))
