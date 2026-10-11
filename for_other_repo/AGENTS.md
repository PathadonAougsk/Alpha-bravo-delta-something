# Manual Pygame Git mergetool on WSL

These instructions are self-contained and can be copied as `AGENTS.md` into
another project. They apply when the user requests Git conflict resolution
through the Feature Branch versus HEAD game. Discover paths and configuration
in the destination project; do not assume this file's original checkout,
interpreter, installed skills, or temporary files exist there.

## Play through Git

Resolve conflicts only through the configured `git mergetool` and its actual
battle windows. Play manually: do not press A, enable `ALWAYS_AUTOBATTLE`,
change stats or RNG, edit conflict files directly, or replace the configured
game with a different tool. The standalone `pygame-battle` MCP server cannot
attach to Git mergetool windows or resolve these conflicts.

Inspect the destination repository and its configuration:

```sh
git rev-parse --show-toplevel
git status --short
git config --get merge.tool
git config --get-regexp '^(merge|mergetool)\.'
```

Run from the repository root. Read the configured game's command to locate
its Python interpreter and entry point; do not execute configuration text
with `eval`. Use that interpreter for the helper below because it needs
Pygame. If this game is not configured, report the missing setup rather than
silently overriding the project's mergetool.

## Accept losses without backups

Do not create backups, copies, snapshots, or recovery archives of the project
or its `.git` directory for this workflow. Do not create protective worktrees
or remote copies to avoid the game's consequences.

The user accepts the actual outcome of playing, including losses. This game's
third consecutive loss deletes the repository's entire `.git` directory,
including local history, branches, configuration, and staged changes. Monitor
`.feature_branch_loss_streak` and report the outcome, but do not stop merely
to avoid reaching the loss limit. Do not reset the counter, rig results,
restore a losing hunk, or manually delete `.git` yourself. If the game deletes
`.git`, report it and stop: Git merge verification is no longer possible.

Git's own temporary merge files and automatic mergetool artifacts may be
created as part of normal operation; do not create additional recovery copies.

## Launch on WSLg

Inspect the current `DISPLAY` and `WAYLAND_DISPLAY`; do not hardcode display
numbers. WSLg may expose both Wayland and X11. Select X11 for the mergetool
process so its window can be inspected and controlled with X11 utilities:

```sh
SDL_VIDEODRIVER=x11 git mergetool --no-prompt
```

Run in a persistent PTY and retain its session ID for battle-result output.
If the execution sandbox blocks local display sockets, use the tool's normal
permission mechanism. A display environment variable does not grant socket
access. Respect any tool rejection; do not bypass it through indirect execution.

Do not launch overlapping mergetool processes. To retry a failed display
launch, interrupt its PTY and verify the associated mergetool and game
processes have exited before restarting. Interrupted launches can leave
Git's temporary merge files behind.

## Manual controls

Inspect the screen before choosing each turn. Direction keys select commands
outright; Return confirms. Send only the keys for the chosen action:

- Attack: `Right Return Return` (select attack, then confirm the HEAD).
- Guard: `Down Return`.
- Health item: `Left Return Return` when the bag selects Health.
- Cancel a submenu: `BackSpace`.
- Toggle the retro filter for readable health numbers: `F1` once per battle.

Wait through the intro or skip it with a separate ordinary key press. The
first ordinary key during the intro only skips it. Wait for the enemy round
to finish before choosing another action. A new battle window follows each
conflict hunk; discover the current window on every call.

Victory keeps the incoming hunk; defeat keeps HEAD. The game writes a file
only after all its hunk battles finish. Closing a battle early leaves that
file unresolved. Accept mixed results and report any resulting disagreement
between files rather than editing around the outcome.

## Portable keyboard and screenshot helper

If a suitable desktop-control tool is available, use it. Otherwise, the
following helper works with this game's 800x600 X11 windows. It requires
`libX11.so.6`, `xwininfo`, and Pygame in the configured game's interpreter.
It uses standard-library ctypes instead of requiring xdotool, Pillow,
ImageMagick, or Python Xlib. Save it in a temporary directory outside the
project, for example with this quoted heredoc:

```sh
cat > /tmp/wsl_mergetool_ui.py <<'PY'
#!/usr/bin/env python3
"""Send chosen menu keys to one live X11 mergetool window and capture it."""

import argparse
import ctypes as C
import re
import subprocess
import time


class KeyEvent(C.Structure):
    _fields_ = [
        ("type", C.c_int), ("serial", C.c_ulong), ("send_event", C.c_int),
        ("display", C.c_void_p), ("window", C.c_ulong), ("root", C.c_ulong),
        ("subwindow", C.c_ulong), ("time", C.c_ulong), ("x", C.c_int),
        ("y", C.c_int), ("x_root", C.c_int), ("y_root", C.c_int),
        ("state", C.c_uint), ("keycode", C.c_uint), ("same_screen", C.c_int),
    ]


class Event(C.Union):
    _fields_ = [("key", KeyEvent), ("pad", C.c_long * 24)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="/tmp/merge-game.png")
    parser.add_argument("--wait", type=float, default=2.6)
    parser.add_argument("keys", nargs="*", choices=[
        "Right", "Left", "Down", "Up", "Return", "BackSpace", "F1",
    ])
    args = parser.parse_args()
    if not 0 <= args.wait <= 10:
        parser.error("--wait must be between 0 and 10 seconds")

    x = C.CDLL("libX11.so.6")
    signatures = {
        "XOpenDisplay": ([C.c_char_p], C.c_void_p),
        "XDefaultRootWindow": ([C.c_void_p], C.c_ulong),
        "XSetInputFocus": ([C.c_void_p, C.c_ulong, C.c_int, C.c_ulong], C.c_int),
        "XStringToKeysym": ([C.c_char_p], C.c_ulong),
        "XKeysymToKeycode": ([C.c_void_p, C.c_ulong], C.c_uint),
        "XSendEvent": ([C.c_void_p, C.c_ulong, C.c_int, C.c_long, C.POINTER(Event)], C.c_int),
        "XFlush": ([C.c_void_p], C.c_int),
        "XGetImage": ([C.c_void_p, C.c_ulong, C.c_int, C.c_int, C.c_uint, C.c_uint, C.c_ulong, C.c_int], C.c_void_p),
        "XGetPixel": ([C.c_void_p, C.c_int, C.c_int], C.c_ulong),
        "XDestroyImage": ([C.c_void_p], C.c_int),
        "XCloseDisplay": ([C.c_void_p], C.c_int),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(x, name)
        function.argtypes = arguments
        function.restype = result
    display = x.XOpenDisplay(None)
    if not display:
        parser.exit(1, "Cannot open DISPLAY; check WSLg and local display permissions.\n")

    try:
        tree = subprocess.run(
            ["xwininfo", "-root", "-tree"], check=True, capture_output=True, text=True,
        ).stdout
        matches = re.findall(r'^\s*(0x[0-9a-fA-F]+) "(Git Merge Tool[^"\n]*)"', tree, re.M)
        if len(matches) != 1:
            parser.exit(1, f"Expected exactly one mergetool window; found {len(matches)}.\n")
        window = int(matches[0][0], 16)
        print(matches[0][1], flush=True)
        root = x.XDefaultRootWindow(display)
        if args.keys:
            x.XSetInputFocus(display, window, 1, 0)
            x.XFlush(display)
            time.sleep(0.25)
        for key in args.keys:
            code = x.XKeysymToKeycode(display, x.XStringToKeysym(key.encode()))
            if not code:
                parser.exit(1, f"No keycode for {key}.\n")
            event = Event()
            event.key = KeyEvent(
                type=2, display=display, window=window, root=root,
                x=400, y=300, keycode=code, same_screen=1,
            )
            if not x.XSendEvent(display, window, 0, 1, C.byref(event)):
                parser.exit(1, "Key press delivery failed.\n")
            x.XFlush(display)
            time.sleep(0.20)
            event.key.type = 3
            if not x.XSendEvent(display, window, 0, 2, C.byref(event)):
                parser.exit(1, "Key release delivery failed.\n")
            x.XFlush(display)
            time.sleep(0.40)
        time.sleep(args.wait)

        # Game/main.py fixes the window at 800x600; its visuals use RGB pixels.
        shot = x.XGetImage(display, window, 0, 0, 800, 600, C.c_ulong(-1).value, 2)
        if not shot:
            parser.exit(1, "No image; the battle window may have closed.\n")
        try:
            pixels = bytearray()
            for row in range(600):
                for col in range(800):
                    value = x.XGetPixel(shot, col, row)
                    pixels.extend(((value >> 16) & 255, (value >> 8) & 255, value & 255))
        finally:
            x.XDestroyImage(shot)
        import pygame
        pygame.image.save(pygame.image.frombuffer(pixels, (800, 600), "RGB"), args.output)
        print(f"Screenshot: {args.output}")
    finally:
        x.XCloseDisplay(display)


if __name__ == "__main__":
    main()
PY
```

Set `merge_game_python` to the interpreter discovered in the destination
project's Git configuration, then run:

```sh
"$merge_game_python" /tmp/wsl_mergetool_ui.py --wait 0 --output /tmp/merge-game.png
"$merge_game_python" /tmp/wsl_mergetool_ui.py --output /tmp/merge-game.png Right Return Return
```

The first command only observes; the second performs one explicitly selected
attack sequence. View the PNG after every action. The helper never chooses
turns and rejects autobattle keys. Use a distinct temporary filename if
another active session already uses these example paths.

`XOpenDisplay` must be checked for failure before calling other X11 functions;
a null pointer can crash the helper. Explicit ctypes signatures preserve
pointer sizes. SDL may expose its title only through `_NET_WM_NAME`, which
`XFetchName` misses; `xwininfo -root -tree` reads the usable title. Inspect
`xprop -id WINDOW_ID _NET_WM_NAME` if discovery fails.

Plain XTest key injection can miss inputs through WSLg. Addressed `XSendEvent`
key press/release events worked for this game's menus. A successful send does
not prove the game accepted an action: inspect the screenshot and PTY output.
The helper handles discrete menu presses; it does not implement held-arrow
DETERMINATION dodging. A standalone MCP dodge wave cannot replace a live Git
mergetool battle.

## Finish and verify

Read the mergetool PTY output to confirm every hunk's result and exit status.
If `.git` remains, check:

```sh
git diff --name-only --diff-filter=U
git ls-files -u
git diff --cached --check
git status --short
```

Inspect the resolved files and report any differences caused by mixed battle
outcomes. Git mergetool stages successful resolutions. Leave the merge
uncommitted unless the user requested a commit. Remove only abandoned
temporary merge files created by the current session, after no mergetool
process is using them. Leave the game's loss counter intact.
