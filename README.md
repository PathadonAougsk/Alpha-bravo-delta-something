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

## Consecutive losses

Each completed hunk battle saves the Feature Branch's consecutive loss count
in `.feature_branch_loss_streak` at the root of the repository containing
`MERGED`. The count persists across files and program runs. A win resets it
to zero; quitting a battle does not change it. Results from earlier completed
battles still count if a later battle is abandoned.

**Three consecutive losses automatically delete that repository's entire
`.git` directory**, including its local history, branches, configuration, and
staged changes. This is destructive. The third loss stops any remaining
battles, leaves `MERGED` untouched, and exits 1. Working files and the saved
loss count remain on disk. Use disposable repositories if you want to try
this behavior.

Loss tracking requires a regular `.git` directory; linked worktrees and
symlinked `.git` directories are rejected before any battle. Standalone
`Game/main.py` battles do not track losses or delete repositories.

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
git config mergetool.keepBackup false
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

Before each battle window closes, the program removes the corresponding
`MERGED.orig` backup if it exists, including when you quit mid-fight. The
`mergetool.keepBackup false` setting above also prevents Git from creating a
new `.orig` backup after the program exits.

## The battle

Arrow keys pick a command on the ring, Enter confirms:

- **ATTACK** - pick a HEAD, then hit it for your attack damage, varied by
  +/-10% on each attack and rounded to a whole number (minimum 1). Choosing
  ATTACK hands the arrows to a cursor on the field rather than spending the
  turn: an orange diamond floats over whoever is picked, left and right walk
  it along the living HEADs, Enter swings and Backspace puts it away.
- **GUARD** - halve the damage you take for the coming round, and give every
  swing that comes in a `GUARD_FIZZLE` (40%) chance of failing outright.
- **ITEM** - heal; you start with three. Taking one out wipes the screen: a
  blue circle opens in the middle of it and grows until there is nothing but
  blue, and then the blue fades off the battle underneath. The retro filter
  is wound up to `PIXELS` (14) along with it and back down again, so the
  heal blocks the whole screen up and it comes back into focus after.
- **DETERMINATION** - only once you are down to half HP or less. Picking it
  opens a text box with your own face in the margin and two ways out laid
  along the bottom of it: Spare, and Flee. Spare and the fight stops being a
  fight: the screen turns into Undertale, a white box with a red heart in it,
  and a wave of bones, bone walls and skulls you have to dodge with nothing
  but the arrows. Survive it and you get the turn back and the whole HP bar
  with it; don't, and the heart breaks.

Every hit that lands puts the number it took off up over the body it came
off, floating up and fading as it goes - the guarded half included, so a
halved blow shows the halved number.

A HEAD whose attack fails against the guard lands on its side: it is drawn
rotated a quarter turn and washed blue, and its next turn goes on picking
itself back up rather than on hitting you. So a guard that catches a swing
costs that HEAD two turns, not one - which is what makes guarding worth a
turn against a HEAD that outweighs you.

### DETERMINATION

DETERMINATION is a last resort rather than an opening move, so the wheel will
not take it while you are still standing comfortably: it opens at
`DETERMINATION_AT` (50%) of your health and stays shut above that. A shut
command is drawn greyed out - sunken button, grey label, even when it is the
one picked - and pressing Enter on it says what it is waiting for and costs
you nothing. It lights up by itself the moment a HEAD takes you under half,
which is also the moment it stops being a stunt: the wave bites with the
HEADs' real damage against whatever HP you have left.

Picking DETERMINATION does not spend the turn either. It opens a text box
across the bottom of the screen - black, ruled in white, with your own face in
the left margin, because the determination is yours to find - and types out
what you have to say a letter at a time, behind the asterisk Undertale
narrates everything with. Enter while it is still typing lands the rest of the
line rather than picking anything. Once the line is up, the two ways out
appear along the bottom of the box with the soul in front of whichever one is
picked and that one lit in Undertale's yellow: left and right walk the pick,
Enter takes it, and Backspace shuts the box without spending the turn. Below
`DETERMINATION_LOW` (25%) of your health the box stops narrating the HEADs and
starts talking to you.

- **Spare** is the dare, and hands the screen to the dodging game below.
- **Flee** is not one: there is no running from a formation that has already
  surrounded you, so the turn is spent finding that out and the HEADs get
  their round.

Sparing them hands the whole screen to the dodging game. The field, the wheel
and the HUD drop away and what is left is a white rule on black with a red
heart sitting in the middle of it - the soul - with the HP counted off
underneath in Undertale's yellow. The arrows move the heart and nothing else
does anything at all: there is no attacking your way out of the wave, and the
turn is spent not being hit.

Six things come at you, on a cadence that tightens as the wave runs, and the
wave escalates: it opens on bones, brings the skulls and the walls out a
third of the way in, and the blue walls halfway.

- **Rain** - bones dropping in through the roof with a column left open.
- **Sweeps** - a rank of them sliding in from one side with a row to slip
  through.
- **Pellets** - they appear hollow around the rim, take their aim at wherever
  the heart is standing, and then come. The aim is taken when they appear, so
  the warning is long enough to walk out of.
- **Walls** - a rank of bone the depth of the box with one slot in it. There
  is no dodging it on the spot: you line the heart up with the slot and ride
  it across.
- **Blue walls** - the same thing with no slot at all, in blue. A blue bone
  only bites what moves, so the way through is to take your hands off the
  arrows and let it pass. It starts most of a box-width outside the box and
  nothing else is thrown while it is on its way or crossing, so what you have
  to stand still through is only ever the wall itself - and the box says what
  the rule is for as long as one is up.
- **Skulls** - a head lines up on the row or the column you are standing in,
  draws a grey line down it, charges where you can see it charging, and then
  the beam is simply on across the whole box for a beat. The charge is the
  dodge; once it is firing there is nothing to do but already be elsewhere.

Hollow is the word for not-yet throughout: a hollow pellet, a grey line, a
shape drawn in outline cannot hit you. Shots are drawn for a run-up outside
the box as well as inside it, so nothing arrives unseen, and the line along
the top of the box drains with the wave, so you can see how much of the turn
is left.

A bone that gets through bites for what the average HEAD swings for, and
leaves the heart flickering and untouchable for a beat afterwards. Both
numbers are the battle's real ones: the wave is as dangerous as the formation
that threw it, and the HP it takes off is HP you do not have for the rest of
the fight. The heart's hitbox is smaller than the heart is drawn, the way it
ought to be.

Run out of HP in there and everything stops: the box goes out from under the
heart, a crack opens down it, it hangs there for a beat and then bursts into
pieces that arc up and fall out of the screen - and that is the game over,
straight into the DEFEAT splash.

Live through it and you get the bar back - all of it, not just what the bones
took. The wave is the hardest thing in the fight and it is only offered at
half health or less, so what a whole round of not being hit pays is a whole
HP bar, which is also what makes walking into one on purpose worth the risk.
Since DETERMINATION shuts again above half health, the full bar locks the
box behind you until a HEAD opens it again.

Live through the wave and the screen goes black, cracks run out from
the middle of it, and the black comes apart into panes that turn over as they
fall away, leaving the battle exactly where you left it - the field, the
HEADs, the HUD and the message - except that it is your turn again. The wave
was the HEADs' round: they have had their swing, so a HEAD the guard put on
its back spends that round getting up, and the guard is spent with it. The
cracking and the panes are the same glass the gun breaks the screen with; it
lives in `glass.py` and both of them hand it the point the blow landed on.

The battle runs at 12 frames a second, which is the retro look working as
intended and is no way to dodge anything, so the loop ticks at
`DETERMINATION_FPS` (48) for as long as the box is up and drops back to 12 the
moment it lets go. Everything in the game is driven off elapsed time rather
than frames, so nothing else notices.

Press **A** on your first turn, before any command has spent it, to start
**autobattle**. The player immediately swings at the picked HEAD and
automatically attacks the next living one on every following turn until
victory or defeat - it drives the field cursor itself, so there is nothing to
confirm. Enemies still take their normal turns; autobattle does not guard,
open the bag or stand its ground. It lasts for the current battle, and
closing the window still quits early. If the intro is running, the first key
only skips it; press A once the fight begins.

To enable autobattle automatically for every battle, set
`ALWAYS_AUTOBATTLE = True` near the top of `Game/battle.py`. Attacks start
after the intro without pressing A. This applies to standalone battles and
Git merge battles. Set it back to `False` to restore manual activation.

Escape does nothing. It is swallowed before anything else sees it, so a
stray press cannot drop you out of a fight, skip the intro or dismiss the
result - closing the window is the way out.

Both Feature Branch and each HEAD roll their damage within that +/-10% spread
on every attack, and every attack has a 2% chance to land a critical hit for
triple the rolled damage. Guard still halves incoming damage, critical hits
included, and the battle message announces each critical hit.

The ring is a wheel, and the selected slot is fixed: picking a command turns
the whole wheel until that command arrives there, rather than moving a
highlight around a standing ring. Every label rides around with it and tilts
as it goes, so neighbours read at `SPACING` degrees (45) and the far one at
90, while whatever is picked is always the upright one. Each arrow still
chooses its own command outright, so a press is one turn of the wheel, not a
step around it. With four commands on it the far one sits 135 degrees round,
where a label would hang over the field upside down, so labels fade out as
they pass 90 and the back of the wheel carries nothing but its button.

Each battle opens on a black screen that splits across the middle: the two
halves part on a lit seam, laid over at `cut.CUT` (45 degrees) so the fight is
let out on a diagonal and the corners of it show first, revealing the player
behind them - a flat blue cut-out standing the full height of the screen. It
shrinks to its own size as it travels to the spot it fights from, and the
moment it lands the colour washes in over the whole frame and the fight
begins. Nothing moves and no input is taken until it has landed; any key skips
it.

When the fight is decided it ends the way the gun does. The last frame of
the battle is caught and held: the blow blows it out - white on a win, red
on a loss - and kicks the lens, cracks run out from the middle of it, and
the whole frozen fight comes apart into panes that turn over as they fall.
What is behind the glass this time is not nothing, though. The splash is
already standing there: a burst of spokes, the player across it huge and
flipped, and VICTORY or DEFEAT stamping over the top, with the whole thing
creeping a few per cent closer the longer it is held.

The last beat is the intro's, run backwards - the same cut, out of the same
`cut.py`, walked the other way. The battle opened on two black halves parting
on a lit seam; it closes on them coming back down, so the corners are the
first thing the black takes and the middle is the last. A win is left framed
by it. A loss waits until the stamp has been up long enough to read, and then
the halves carry on until they meet and the screen is shut. The ending sets
its own length (`Outro.total`, about three seconds) and the window closes on
its own after it, so the next hunk's battle - or the next file - follows
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

The song goes in the same folder, as `opening.ogg` (or `.mp3`, or `.wav`). It
starts with the battle at 80% volume, holds there for three seconds while the
intro lifts, then slides down to 10% and stays there, looping under the rest
of the fight. No file, no mixer or no audio device and the battle simply runs
quiet.

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

Run the automated battle and merge checks from the repository root (deletion
checks use disposable temporary directories):

```sh
python -m unittest discover -s tests
```

## Credits

The opening song is **"It's Going Down Now"** from *Persona 3 Reload*
(ATLUS / SEGA). Taken from:

<https://www.youtube.com/watch?v=v6PDPMQVGDM>

The audio file itself is not in this repository - drop your own copy in
`Assets/` as `opening.ogg` and the game will pick it up.
