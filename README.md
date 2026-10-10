# Pygame Git mergetool

`main.py` is the Git-facing entry point. It reads the four merge files, then
hands off to the turn-based battle in `Game/main.py`: you play **Feature
Branch**, and every conflict hunk in `$MERGED` gets **its own battle** against
the single **HEAD** guarding it. Three conflict hunks means three fights.

- Win a battle, and that hunk keeps the feature branch's side.
- Lose a battle, and that hunk keeps HEAD's side.
- Close the window mid-fight and `$MERGED` is left untouched - every hunk,
  including the ones already won, since the file is written only once all the
  battles are done.

Each hunk is decided on its own, so one file can end up part HEAD, part feature
branch. Only the conflicted hunks are rewritten. Lines Git already merged
cleanly stay exactly as they are, and the conflict markers are removed either
way.

## Stats come from the conflict

Neither fighter has stats of its own: each one is as strong as the side of the
hunk it is fighting for, measured in bytes. The HEAD is built from what HEAD
holds, you are built from what the incoming branch holds, and every byte is
worth 0.1% on that side's baseline. Rewrite a block wholesale and you walk in
with the stats to match; change a line by three characters against HEAD's 120
and you are ahead by 0.3%, which is worth about as much as it sounds.

An evenly split hunk is a close fight, so the `HEAD_BASELINE` in `main.py`
starts higher than `PLAYER_BASELINE`: you move first and carry three items, so
parity costs the HEAD more on paper. Both constants and the per-byte rate are
at the top of `main.py`. Since the HEAD's size on screen is drawn from its
health, the side holding more of the hunk also looks the part, up to the
`MAX_RADIUS` that keeps it on the field.

Install the dependency:

```sh
python -m pip install -r requirements.txt
```

Configure Git in the repository where you want to use the tool, replacing both
absolute paths below with your Python interpreter and this project's `main.py`:

```sh
git config merge.tool pygame
git config mergetool.pygame.cmd '"/absolute/path/to/python" "/absolute/path/to/main.py" "$BASE" "$LOCAL" "$REMOTE" "$MERGED"'
git config mergetool.pygame.trustExitCode true
```

Then run `git mergetool` during a merge conflict. Git passes four file paths:

- `BASE`: the common ancestor.
- `LOCAL`: the current branch (HEAD).
- `REMOTE`: the branch being merged, such as your feature branch.
- `MERGED`: the working file containing conflict markers.

The program reads all four files as bytes. Once every battle is finished it
writes each hunk's winning side into `$MERGED` and exits 0, so Git marks the
conflict resolved, printing which side took each hunk. Quitting before the
battles are over exits 1 and leaves the file alone. If the markers in `$MERGED`
do not pair up, nothing is played and nothing is written: there is no end of a
hunk for a battle to decide.

## The battle

Arrow keys pick a command on the ring, Enter confirms:

- **ATTACK** - hit the targeted HEAD for your attack damage.
- **GUARD** - halve the damage you take for the coming round.
- **ITEM** - heal; you start with three.

The ring is a wheel, and the selected slot is fixed: picking a command turns
the whole wheel until that command arrives there, rather than moving a
highlight around a standing ring. Every label rides around with it and tilts
as it goes, so neighbours read at `SPACING` degrees (45) and the far one at
90, while whatever is picked is always the upright one. Each arrow still
chooses its own command outright, so a press is one turn of the wheel, not a
step around it.

Each battle opens on a black screen that splits across the middle: the two
halves part on a lit seam to reveal the player behind them, a flat blue cut-out
standing the full height of the screen. It shrinks to its own size as it
travels to the spot it fights from, and the moment it lands the colour washes
in over the whole frame and the fight begins. Nothing moves and no input is
taken until it has landed; any key skips it.

When the fight is decided the field gives way to a splash: a white-out, a
burst of spokes, and the player across it huge and flipped, with VICTORY or
DEFEAT stamped over the top. It holds for a couple of seconds and the window
closes on its own, so the next hunk's battle - or the next file - follows
without waiting. The window title counts the hunks off: `conflict 2/3`.

The HUD is drawn square: hard corners, no rounding.

### The retro filter

The whole frame is drawn at full size, then crunched down to a fraction of it
and blown back up with nearest-neighbour, so everything on screen - sprites,
shapes, text alike - comes out in chunky pixels. One number controls it and
nothing else in the game has to know about it:

```sh
python Game/main.py --retro=2   # the default
python Game/main.py --retro=1   # off
python Game/main.py --retro=4   # unreadable, but very retro
```

**F1** toggles it off and back on mid-battle, which is worth knowing because
the filter costs legibility: at 3 the message strip and the HUD numbers start
to go, and by 4 they are gone. Separately, every asset is now scaled
nearest-neighbour rather than smoothed, so a blown-up sprite reads as bigger
pixels instead of a blurrier picture - that applies whether the filter is on
or not.

The art lives in `Assets/`: `makoto.png` (the player), `monster1.png` (the
HEAD), `bg1.png` (the wall, drawn once and zoomed to fill it), `floor.png`
(tiled floor), `sword.png` (held in the player's hand) and `icon.png` (the
window icon). Any file that is missing simply falls back to the plain shapes,
so the game still runs without them.

The sword is held rather than pointed at anything, so the target a command
would hit is the one whose name is lit up.

### What moves

Nothing on the field is still. Both fighters breathe on the spot, step into
the blow when they attack, flash white and recoil when one lands, and a beaten
HEAD fades out and slumps off the field rather than blinking away. Health and
mana bars chase their numbers instead of jumping, leaving a pale sliver over
the ground they have yet to cover. The command ring breathes, the picked
button swells and the wheel eases round to it, each message slides in from the
left, and the wall drifts behind it all - zooming to cover always leaves more
image than the opening shows, so it can pan without ever revealing an edge. The floor is deliberately the exception: scrolling the ground underfoot
would read as the fighters walking off it.

Every timing is a named constant near the top of the file it belongs to, so
any of it can be slowed down, sped up or set to zero on its own.

Every stat comes from a baseline with a small random spread, so no two fights
are identical even over hunks of the same size. The mergetool sets both
baselines from the bytes each side holds and always plays `--amount=1`; run the
game on its own to pick the baselines by hand and fight any number of enemies:

```sh
python Game/main.py --base=50 --enemy=168 --amount=1
```
