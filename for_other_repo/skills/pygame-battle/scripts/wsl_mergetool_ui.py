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
