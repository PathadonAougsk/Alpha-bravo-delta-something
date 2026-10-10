"""The opening song: loud enough to announce the fight, then out of the way.

The battle starts on the song at full voice, holds it there for HOLD seconds
- long enough to be the thing you are listening to - and then slides it down
to QUIET, where it sits under the rest of the fight for as long as the fight
lasts.

The song is "It's Going Down Now" from Persona 3 Reload (ATLUS / SEGA):
https://www.youtube.com/watch?v=v6PDPMQVGDM - the file itself is not in the
repository, so it goes in Assets/ under one of the OPENING names below.

Everything in here is optional. No mixer, no audio device, no song in
Assets/: each one leaves the whole module doing nothing, the same way a
missing image leaves `assets` handing back None. A sketch with no sound card
still runs the battle.
"""

import pygame

from assets import ASSETS_DIR

# the first of these that is actually in Assets/ is the song
OPENING = ("opening.ogg", "opening.mp3", "opening.wav")

LOUD = 80   # out of 100: what the song opens at...
QUIET = 10  # ...and what it settles to for the rest of the battle
HOLD = 3.0  # seconds it stays up there before it starts coming down
EASE = 1.5  # and seconds the slide down itself takes; 0 to drop straight


def _song():
    """The song's path, or None when there is no song to play."""
    for name in OPENING:
        path = ASSETS_DIR / name
        if path.is_file():
            return path
    return None


class Music:
    """The song and where it is in its climb down. Silent when it cannot play."""

    def __init__(self):
        self.live = False
        self.elapsed = 0.0

    @property
    def level(self):
        """Where the volume is right now, on the same 0-100 the constants are on."""
        if self.elapsed < HOLD:
            return LOUD
        if EASE <= 0:
            return QUIET  # no slide asked for: it is simply quiet from here
        over = (self.elapsed - HOLD) / EASE
        if over >= 1.0:
            return QUIET
        return LOUD + (QUIET - LOUD) * over

    def start(self):
        """Open the mixer and set the song going. False when it cannot."""
        path = _song()
        if path is None:
            return False
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(LOUD / 100)
            pygame.mixer.music.play(-1)  # it is the battle's music too, so it loops
        except pygame.error:
            return False  # no device, or nothing that can read the file
        self.live = True
        self.elapsed = 0.0
        return True

    def advance(self, dt):
        """Carry the volume along the hold and the slide that follows it."""
        if not self.live or self.elapsed >= HOLD + EASE:
            return
        self.elapsed += dt
        try:
            pygame.mixer.music.set_volume(self.level / 100)
        except pygame.error:
            self.live = False

    def stop(self):
        """Cut the song and let the mixer go, on the way out of the battle."""
        if not self.live:
            return
        self.live = False
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except pygame.error:
            pass
