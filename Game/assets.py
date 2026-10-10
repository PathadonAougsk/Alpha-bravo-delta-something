"""Loading the images in Assets/.

Every lookup returns None when the file is missing or unreadable, so the game
still draws with its plain shapes if the folder is not there.
"""

from math import ceil
from pathlib import Path

import pygame

ASSETS_DIR = Path(__file__).resolve().parent.parent / "Assets"

ICON = "icon.png"
PLAYER = "makoto.png"
# Every HEAD rolls one of these at spawn, so a row of them is a mixed bunch.
ENEMIES = ("monster1.png", "verity.png", "plummet.png", "baibai.png", "persona.png")
ENEMY = ENEMIES[0]
BACKGROUND = "bg1.png"
FLOOR = "floor.png"
SWORD = "sword.png"

_cache = {}
_fonts = {}


def font(size, bold=True):
    """A system font at `size`, kept for the rest of the battle."""
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(None, size, bold=bold)
    return _fonts[key]


def load(name):
    """Load an asset once and keep it. None when it cannot be read."""
    if name not in _cache:
        try:
            _cache[name] = pygame.image.load(ASSETS_DIR / name).convert_alpha()
        except (pygame.error, OSError):
            _cache[name] = None
    return _cache[name]


def by_height(name, height):
    """The asset scaled to `height`, keeping its aspect ratio. None when missing.

    Nearest-neighbour throughout: the art is pixel art, and smoothing it on the
    way up turns the pixels into mush. Scaling this way keeps every edge hard,
    so a blown-up asset reads as bigger pixels rather than a blurrier picture.
    """
    key = (name, height)
    if key not in _cache:
        image = load(name)
        if image is None:
            _cache[key] = None
        else:
            width = round(image.get_width() * height / image.get_height())
            _cache[key] = pygame.transform.scale(image, (width, height))
    return _cache[key]


def tile(surface, name, rect):
    """Tile an asset across `rect`. False when the asset is missing."""
    image = load(name)
    if image is None:
        return False
    previous = surface.get_clip()
    surface.set_clip(rect)
    step_x, step_y = image.get_size()
    for y in range(rect.top, rect.bottom, step_y):
        for x in range(rect.left, rect.right, step_x):
            surface.blit(image, (x, y))
    surface.set_clip(previous)
    return True


def flashed(image, amount):
    """A copy of `image` washed towards white by `amount` (0 to 1).

    Not cached: a hit flash lasts a third of a second and the surfaces are
    small, so a fresh copy each frame is cheaper than keeping them all around.
    """
    if amount <= 0:
        return image
    level = round(190 * min(1.0, amount))
    lit = image.copy()
    lit.fill((level, level, level), special_flags=pygame.BLEND_RGB_ADD)
    return lit


def tinted(image, color, amount):
    """A copy of `image` washed towards `color` by `amount` (0 to 1).

    Not cached, for the same reason `flashed` is not: the wash only lasts as
    long as a HEAD is down, and the surfaces are small.
    """
    if amount <= 0:
        return image
    amount = min(1.0, amount)
    washed = image.copy()
    # pull every channel down, then add the tint back in: a multiply alone only
    # ever darkens the art and an add alone only ever washes it out
    keep = round(255 * (1 - amount))
    washed.fill((keep, keep, keep), special_flags=pygame.BLEND_RGB_MULT)
    washed.fill(
        tuple(round(c * amount) for c in color), special_flags=pygame.BLEND_RGB_ADD
    )
    return washed


def cover(surface, name, rect, offset=(0, 0)):
    """Draw an asset once, zoomed to fill `rect`. False when the asset is missing.

    `offset` slides the zoomed image behind the rect, which is free: zooming to
    cover always leaves more image than the rect can show.
    """
    key = (name, "cover", rect.size)
    if key not in _cache:
        image = load(name)
        if image is None:
            _cache[key] = None
        else:
            # the larger of the two ratios, so the short side still reaches the edge
            scale = max(rect.width / image.get_width(), rect.height / image.get_height())
            size = (ceil(image.get_width() * scale), ceil(image.get_height() * scale))
            _cache[key] = pygame.transform.scale(image, size)
    zoomed = _cache[key]
    if zoomed is None:
        return False
    previous = surface.get_clip()
    surface.set_clip(rect)
    centre = (rect.centerx + offset[0], rect.centery + offset[1])
    surface.blit(zoomed, zoomed.get_rect(center=centre))  # centre crop
    surface.set_clip(previous)
    return True


def reset():
    """Drop every cached surface.

    Each battle sets up its own display, and a surface converted for the
    previous one has no business being blitted onto the next. The fonts go
    with them: they were opened under the last battle's pygame.init().
    """
    _cache.clear()
    _fonts.clear()
