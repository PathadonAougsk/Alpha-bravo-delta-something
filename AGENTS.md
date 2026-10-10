# Repository Guidelines

## Project Structure & Module Organization

This Python/Pygame Git mergetool resolves each conflict hunk through a turn-based battle.
- Root `main.py` reads merge files, parses conflicts, calculates fighter baselines, and writes the resolved file.
- `Game/main.py` runs the game and rendering loop. Supporting modules separate combat (`battle.py`), fighters (`entity.py`, `player.py`, `enemy.py`), stats, menus, and intro/outro animations.
- `Assets/` contains PNG sprites, backgrounds, and the window icon; `Game/assets.py` handles loading and fallback shapes.
- `README.md` documents gameplay and Git integration. `test.txt` is sample text, not an automated test suite.

## Build, Test, and Development Commands

Run commands from the repository root with a Python interpreter available as `python` (or substitute `python3`):
- `python -m pip install -r requirements.txt` installs Pygame, the sole declared dependency. Prefer a virtual environment.
- `python Game/main.py --base=50 --enemy=168 --amount=1` launches a standalone battle.
- `python Game/main.py --retro=1` disables the retro filter for visual inspection.
- `python main.py BASE LOCAL REMOTE MERGED` resolves conflicts using four file paths; use disposable fixtures during development.
- `python -m compileall -q main.py Game` checks Python syntax.

There is no separate build step. Configure `git mergetool` using the absolute-path example in `README.md`.

## Coding Style & Naming Conventions

Use four-space indentation, snake_case functions and variables, PascalCase classes, and UPPER_SNAKE_CASE constants. Keep tuning values near module tops. Follow existing import grouping: standard library, Pygame, then local modules. Preserve flat imports within `Game/`. Use concise docstrings for behavior and return values. No formatter or linter is configured.

## Testing Guidelines

No automated framework or coverage threshold is configured. Manually verify attack, guard, healing, victory/defeat, quitting, and F1 filter toggling. For merge changes, check multiple hunks, diff3 markers, malformed markers, and byte/line-ending preservation. Abandoning any battle must leave the entire merged file untouched. If adding automated tests, use `tests/test_*.py` and document their runner.

## Commit & Pull Request Guidelines

History uses short, informal subjects such as `added sword`; no enforced convention is evident. Write concise, action-oriented subjects describing the change. PRs should explain behavior changes, list validation performed, link relevant issues, and include screenshots for visual changes. Update `README.md` when controls, command-line options, or merge behavior changes.
