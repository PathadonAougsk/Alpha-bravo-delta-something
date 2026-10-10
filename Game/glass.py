"""Glass: the cracks that run out from a point, and the panes they leave.

Two screens break in this game - the one the gun takes out and the one the
determination box comes back through - and they break the same way, so the geometry
of it lives here rather than in either of them. Nothing in here knows what it
is cutting up: hand it a surface and the point the blow landed on.
"""

import math
import random

import pygame


def cracks(origin, reach, count, kinks, seed, branch=0.0, wander=0.38):
    """Jagged lines running out from `origin`, rolled once off `seed`.

    Each line comes back as `(begun, points)`, where `begun` is how far
    through the run it starts: a line thrown off a kink does not begin
    growing until the crack it came off has reached that kink.
    """
    rolls = random.Random(seed)
    origin = pygame.Vector2(origin)
    lines = []
    for _ in range(count):
        angle = rolls.uniform(0, math.tau)
        point = pygame.Vector2(origin)
        line = [point]
        for _ in range(kinks):
            angle += rolls.uniform(-wander, wander)  # it wanders as it runs
            step = reach / kinks * rolls.uniform(0.7, 1.3)
            point = point + pygame.Vector2(math.cos(angle), math.sin(angle)) * step
            line.append(point)
        lines.append((0.0, line))

        if rolls.random() < branch:
            at = rolls.randrange(1, kinks)
            off = angle + rolls.choice((-1, 1)) * rolls.uniform(0.5, 1.1)
            point = line[at]
            twig = [point]
            for _ in range(kinks - at):
                off += rolls.uniform(-0.3, 0.3)
                step = reach / kinks * rolls.uniform(0.6, 1.1)
                point = point + pygame.Vector2(math.cos(off), math.sin(off)) * step
                twig.append(point)
            if len(twig) > 1:
                lines.append((at / kinks, twig))
    return lines


def draw_cracks(surface, lines, grown, color, core=None, width=4):
    """Draw `lines` as far out from their roots as they have got.

    `core` is laid down inside the line, two pixels thinner, so a crack reads
    as lit glass rather than as a stroke of one flat colour.
    """
    for begun, line in lines:
        if grown <= begun:
            continue
        reached = (grown - begun) / (1 - begun) * (len(line) - 1)
        points = [line[0]]
        for i in range(1, len(line)):
            if reached >= i:
                points.append(line[i])
                continue
            part = reached - (i - 1)
            if part > 0:
                points.append(line[i - 1].lerp(line[i], part))
            break
        if len(points) > 1:
            pygame.draw.lines(surface, color, False, points, width)
            if core is not None and width > 2:
                pygame.draw.lines(surface, core, False, points, width - 2)


def shatter(frozen, origin, count, stagger=0.45, edge=None, edge_width=3, spin=52):
    """Cut `frozen` into `count` wedges meeting at `origin`, ready to fly off.

    The wedges run far enough past the surface that the straight edge at the
    far end of one is never in shot: what is left inside the frame is a clean
    slice of glass, cropped to the only part of it anybody sees. Each comes
    back with where it sits, the way out of the frame it leans, and the turn
    it takes on the way.
    """
    screen = frozen.get_rect()
    origin = pygame.Vector2(origin)
    reach = math.hypot(*screen.size) * 6
    slice_ = math.tau / count
    edges = sorted(
        i * slice_ + random.uniform(-stagger, stagger) * slice_ for i in range(count)
    )

    panes = []
    for i, start in enumerate(edges):
        end = edges[(i + 1) % count]
        if end <= start:
            end += math.tau
        corners = [
            origin,
            origin + pygame.Vector2(math.cos(start), math.sin(start)) * reach,
            origin + pygame.Vector2(math.cos(end), math.sin(end)) * reach,
        ]
        xs = [p.x for p in corners]
        ys = [p.y for p in corners]
        box = pygame.Rect(
            min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        ).clip(screen)
        if not box.width or not box.height:
            continue

        local = [(p.x - box.x, p.y - box.y) for p in corners]
        shape = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.polygon(shape, (255, 255, 255, 255), local)
        pane = pygame.Surface(box.size, pygame.SRCALPHA)
        pane.blit(frozen, (-box.x, -box.y))
        pane.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if edge is not None:
            pygame.draw.polygon(pane, edge, local, edge_width)  # the lit break edge

        middle = (start + end) / 2
        panes.append(
            {
                "image": pane,
                "spot": pygame.Vector2(box.center),
                "away": pygame.Vector2(math.cos(middle), math.sin(middle)),
                "spin": random.uniform(-spin, spin),
            }
        )
    return panes
