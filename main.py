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
import os
import shutil
import sys
import tempfile
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent / "Game"
LOSS_STREAK_FILE = ".feature_branch_loss_streak"
LOSS_LIMIT = 3

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


def remove_merge_backup(merged):
    """Remove this merge's .orig backup, if present."""
    backup = merged.with_name(merged.name + ".orig")
    try:
        backup.unlink(missing_ok=True)
    except OSError as error:
        print(f"Could not remove {backup}: {error}", file=sys.stderr)


def find_repository_root(merged):
    """Find the merged file's repository, requiring a real .git directory."""
    directory = merged.resolve().parent
    for candidate in (directory, *directory.parents):
        git_dir = candidate / ".git"
        if git_dir.is_symlink() or git_dir.exists():
            if git_dir.is_symlink() or not git_dir.is_dir():
                raise ValueError(
                    f"{git_dir}: loss tracking requires a regular .git directory; "
                    "linked worktrees and symlinks are unsupported"
                )
            return candidate
    raise ValueError(f"{merged}: no repository with a .git directory found")


def read_loss_streak(repository):
    """Read the persisted streak; a new repository starts at zero."""
    path = repository / LOSS_STREAK_FILE
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return 0
    if not value.isascii() or not value.isdecimal():
        raise ValueError(f"{path}: expected a nonnegative integer loss streak")
    return int(value)


def record_battle_result(repository, streak, won):
    """Persist a completed battle and remove .git at the loss limit."""
    streak = 0 if won else streak + 1
    path = repository / LOSS_STREAK_FILE
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=repository,
            prefix=LOSS_STREAK_FILE + ".", delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(f"{streak}\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    print(f"Feature Branch: {streak} consecutive loss(es) (saved in {path}).")
    if streak >= LOSS_LIMIT:
        git_dir = repository / ".git"
        if git_dir.is_symlink() or not git_dir.is_dir():
            raise ValueError(f"Refusing to remove {git_dir}: not a regular directory")
        print(f"Feature Branch lost {LOSS_LIMIT} times in a row; removing {git_dir}.")
        shutil.rmtree(git_dir)
    return streak


def fight_conflicts(game, pieces, merged):
    """Play each hunk; return None on abandonment or repository deletion."""
    repository = find_repository_root(merged)
    streak = read_loss_streak(repository)
    filename = merged.name
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
            before_close=lambda: remove_merge_backup(merged),
        )
        if won is None:
            return None
        streak = record_battle_result(repository, streak, won)
        if streak >= LOSS_LIMIT:
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
    try:
        keep_head = fight_conflicts(game, pieces, args.merged)
    except (OSError, ValueError) as error:
        print(f"{name}: could not track battle results: {error}", file=sys.stderr)
        return 1
    if keep_head is None:
        print(f"{name}: battles stopped, merged file left untouched.")
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
