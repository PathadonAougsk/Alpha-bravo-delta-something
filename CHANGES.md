# Changes compared with `main`

## Comparison scope

- Current branch: `feat/various`, commit `63bb4fc87480e7155aa0464bba9b5b700d5a1936`.
- Baseline: local `main`, commit `0d393e42247b79558b8bf50d926c02f08169e8f8`.
- Local `main` and `origin/main` point to the same commit at comparison time; no remote fetch was performed.
- `main` is an ancestor of the current branch. The comparison uses `git diff main...HEAD` and covers one additional commit.
- The working tree was clean before this report was created.
- The branch changes 16 files: 492 inserted lines and 18 deleted lines across nine text files, plus seven modified Python bytecode files. These totals exclude this report.

## Main behavior changes

### Persistent loss tracking and repository deletion

Root `main.py` now records each completed conflict-hunk battle in `.feature_branch_loss_streak` at the root of the repository containing `MERGED`.

- A defeat increments the counter; a victory resets it to zero.
- The counter persists across files and program runs.
- Quitting does not record a result, but earlier completed battles still count when a later battle is abandoned.
- Counter updates use a temporary file followed by `os.replace`.
- Missing counters start at zero; malformed counters stop resolution before any battle begins.

**At three consecutive defeats, the tool recursively deletes that repository's entire `.git` directory.** This removes Git metadata, including local history, branches, configuration, and the index. Working files and the loss counter remain.

The third defeat also stops remaining battles, leaves `MERGED` untouched, and returns exit status 1. A failure to save the counter or remove the directory also returns 1 without writing a resolved merge file; deletion failures may occur after some Git metadata has already been removed.

Repository discovery walks upward from the merged file's resolved location and requires a regular `.git` directory. Linked worktrees, `.git` files, and symlinked `.git` directories are rejected. Conflict resolution now requires such a repository, whereas the previous battle loop did not check for one. Standalone `Game/main.py` battles do not use loss tracking or delete Git metadata.

### Merge backup cleanup

`Game/main.py` accepts an optional `before_close` callback. Root `main.py` supplies a callback that removes `MERGED.orig` before each battle window closes, including after an early quit.

- A missing backup is harmless; removal errors are printed to standard error.
- `pygame.quit()` runs in a `finally` block around the callback.
- The README's Git configuration example adds `mergetool.keepBackup false` to prevent Git from creating another backup after the tool exits.

Although abandoning a battle still leaves `MERGED` unchanged, its `.orig` backup can now be removed.

### First-turn autobattle

`Game/battle.py` and `Game/main.py` add autobattle activated with **A** on the opening player turn, before a turn-consuming command is used.

- Activation immediately attacks the current target.
- Each subsequent player turn automatically attacks the next living enemy, using the existing enemy turns and resolution timing.
- Autobattle uses neither guard nor healing items and blocks manual battle commands once enabled.
- It ends with victory or defeat, and each new battle starts in manual mode. Escape and window closing remain available to quit.
- An unavailable item or an unknown command does not consume the activation opportunity.
- The initial battle message advertises the key, and an on-screen label shows availability or `AUTOBATTLE ACTIVE`.
- During the intro, the first key skips the intro; activation requires pressing A after the fight begins.

### Damage variation and critical hits

`Game/entity.py` changes attacks from fixed damage to randomized damage for both the player and enemies.

- Damage varies by +/-10% of the attack stat, rounds to a whole number, and has a minimum of 1 before critical multiplication.
- Every attack has a 2% critical-hit chance; a critical triples the rolled damage.
- Guard continues to halve incoming damage, including critical damage.
- Entities expose whether their latest attack was critical through `last_attack_critical`.

`Game/battle.py` now reports the actual health removed by a player attack, matching the existing enemy damage reporting. Both sides' messages announce critical hits. Defeat messages retain the final attack's damage and critical information before announcing defeat.

## Dependency, documentation, and repository changes

| File or group | Change |
| --- | --- |
| `requirements.txt` | Replaces `pygame` with `pygame-ce`; application imports continue to use `pygame`. No version is pinned. |
| `README.md` | Documents loss persistence and deletion, repository restrictions, backup cleanup, autobattle controls, damage variation, critical hits, and the test runner. |
| `AGENTS.md` | Adds repository guidance covering module structure, development commands, coding conventions, validation, and commits/PRs. |
| `Game/__pycache__/*.cpython-314.pyc` | Updates seven tracked bytecode files: battle, command menu, enemy, entity, main, player, and stats. The corresponding command menu, enemy, player, and stats source files have no changes in this comparison. |

The conflict parser, byte-based fighter baseline calculation, sprites/assets, and rendering filter have no source changes in this branch.

## New automated tests

The branch adds two standard-library `unittest` modules, with 18 test methods in total:

- `tests/test_battle.py`: seven tests covering immediate autobattle activation, turn timing, retargeting, victory/defeat, activation restrictions, rejected manual input during autobattle, and fresh-battle state. Random attack rolls are mocked for deterministic results.
- `tests/test_merge.py`: eleven tests covering persistent losses, reset on victory, deletion on the third loss, stopping remaining hunks, quitting, malformed counters, counter-save and deletion failures, worktree/symlink rejection, and clean or malformed conflict input. The fixtures also check byte and line-ending preservation. Repository-deletion checks use temporary directories.

The documented runner is:

```sh
python -m unittest discover -s tests
```

These tests do not directly exercise critical-hit probabilities, damage-spread boundaries, the Pygame key/rendering loop, or the backup callback.

## Validation performed for this report

The commit history, complete text diff, changed-file list, and diff statistics were inspected.

Running `python3 -B -m unittest discover -s tests` passed all 11 merge tests. The battle test module could not import because the available Python interpreter lacks `pygame`, so its seven tests did not run and the overall command exited 1. No interactive gameplay validation was performed.
