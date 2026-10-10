"""Pygame Git mergetool: settle each conflict with its own turn-based battle.

Git hands over four files; Game/main.py runs one fight per conflict hunk in
$MERGED - Feature Branch (you) against the single HEAD standing guard over that
hunk - and each hunk keeps the side that won its own battle.

Each fighter's stats come from the side of the hunk it is fighting for: the
HEAD from the bytes HEAD holds, the player from the bytes the incoming branch
holds. The side that wrote more goes in stronger, so a hunk where the incoming
branch holds 123 bytes against HEAD's 120 gives the player a 0.3% edge.
"""

import argparse
import importlib.util
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent / "Game"

# What each side of a hunk fights at. A side's baseline is its empty-handed
# value plus PER_BYTE for every byte it holds, so the bigger half of a conflict
# brings the better stats and an even split is an even fight.
PLAYER_BASELINE = 50.0   # an incoming side holding nothing fights at this
HEAD_BASELINE = 168.0    # and an empty HEAD at this: the player moves first and
                         # carries three items, so parity needs HEAD ahead on paper
PER_BYTE = 0.001         # every byte a side holds is worth 0.1% on its baseline

# Git's conflict markers, in the order they appear in $MERGED.
CONFLICT_MARKER = b"<<<<<<<"   # start of the HEAD side
BASE_MARKER = b"|||||||"       # common ancestor, diff3 style only
SPLIT_MARKER = b"======="      # HEAD side ends, feature branch side begins
END_MARKER = b">>>>>>>"        # end of the hunk


def load_game():
    """Import Game/main.py, with Game/ on sys.path so its flat imports resolve."""
    if str(GAME_DIR) not in sys.path:
        sys.path.insert(0, str(GAME_DIR))
    spec = importlib.util.spec_from_file_location("game_main", GAME_DIR / "main.py")
    game = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(game)
    return game


def split_conflicts(merged):
    """Break $MERGED into the pieces Git left behind, in order.

    A bytes piece is text Git merged cleanly and is kept as it is; a
    (head, feature) tuple is one conflict hunk, one battle, two candidate
    versions. Returns None if the markers do not pair up.
    """
    pieces, clean, head_side, feature_side = [], [], [], []
    state = "clean"

    for line in merged.splitlines(keepends=True):
        if state == "clean":
            if line.startswith(CONFLICT_MARKER):
                pieces.append(b"".join(clean))
                clean, head_side, feature_side = [], [], []
                state = "head"
            else:
                clean.append(line)
        elif state == "head":
            if line.startswith(BASE_MARKER):
                state = "base"
            elif line.startswith(SPLIT_MARKER):
                state = "feature"
            else:
                head_side.append(line)
        elif state == "base":
            if line.startswith(SPLIT_MARKER):
                state = "feature"
        elif state == "feature":
            if line.startswith(END_MARKER):
                pieces.append((b"".join(head_side), b"".join(feature_side)))
                state = "clean"
            else:
                feature_side.append(line)

    if state != "clean":
        return None
    pieces.append(b"".join(clean))
    return pieces


def count_conflicts(pieces):
    """How many conflict hunks are in `pieces` - one battle stands over each."""
    return sum(1 for piece in pieces if isinstance(piece, tuple))


def resolve_conflicts(pieces, keep_head):
    """Rebuild the file, each hunk taking the side that won its own battle.

    `keep_head` holds one flag per hunk, in the order the hunks appear.
    """
    verdicts = iter(keep_head)
    out = []
    for piece in pieces:
        if isinstance(piece, tuple):
            head_side, feature_side = piece
            out.append(head_side if next(verdicts) else feature_side)
        else:
            out.append(piece)
    return b"".join(out)


def baseline(length, empty_handed):
    """What a side of a hunk fights at, given the bytes it holds."""
    return round(empty_handed * (1 + PER_BYTE * length), 4)


def fight_conflicts(game, pieces, filename):
    """Play one single-enemy battle per hunk. None if a battle is abandoned."""
    hunks = [piece for piece in pieces if isinstance(piece, tuple)]
    total = len(hunks)
    keep_head = []

    for number, (head_side, feature_side) in enumerate(hunks, start=1):
        # each fighter is only as strong as the side it is fighting for
        head_stats = baseline(len(head_side), HEAD_BASELINE)
        player_stats = baseline(len(feature_side), PLAYER_BASELINE)
        print(
            f"{filename}: conflict {number}/{total} - "
            f"HEAD holds {len(head_side)}B (baseline {head_stats}), "
            f"incoming holds {len(feature_side)}B (baseline {player_stats})."
        )
        won = game.main(
            [f"--base={player_stats}", f"--enemy={head_stats}", "--amount=1"],
            title=f"Git Merge Tool - {filename} - conflict {number}/{total}",
        )
        if won is None:
            return None
        keep_head.append(not won)

    return keep_head


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path, help="Common ancestor file ($BASE)")
    parser.add_argument("local", type=Path, help="Current branch file ($LOCAL)")
    parser.add_argument("remote", type=Path, help="Incoming branch file ($REMOTE)")
    parser.add_argument("merged", type=Path, help="Working file with conflicts ($MERGED)")
    args = parser.parse_args()

    # Keep the original bytes, including conflict markers and line endings.
    try:
        merge_content = {
            name: getattr(args, name).read_bytes()
            for name in ("base", "local", "remote", "merged")
        }
    except OSError as error:
        parser.error(str(error))

    name = args.merged.name
    pieces = split_conflicts(merge_content["merged"])
    if pieces is None:
        # Nothing is played: a battle cannot pick a side of a hunk that has no end.
        print(f"{name}: conflict markers do not pair up, left unresolved.", file=sys.stderr)
        return 1

    total = count_conflicts(pieces)
    if total == 0:
        print(f"{name}: no conflict hunks to fight over, left as it is.")
        return 0

    game = load_game()
    print(f"{name}: {total} conflict hunk(s), {total} battle(s) to play.")
    keep_head = fight_conflicts(game, pieces, name)
    if keep_head is None:
        print(f"{name}: battle abandoned, conflict left unresolved.")
        return 1

    try:
        args.merged.write_bytes(resolve_conflicts(pieces, keep_head))
    except OSError as error:
        print(f"Could not write {args.merged}: {error}", file=sys.stderr)
        return 1

    for number, head_won in enumerate(keep_head, start=1):
        winner = (
            "HEAD wins - kept the current branch side"
            if head_won
            else "Feature Branch wins - kept the incoming side"
        )
        print(f"{name}: conflict {number}/{total} - {winner}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
