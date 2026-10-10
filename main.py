"""Minimal Pygame entry point for Git mergetool."""

import argparse
from pathlib import Path


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

    import pygame

    pygame.init()
    try:
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Git Merge Tool")
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            screen.fill((30, 30, 30))
            pygame.display.flip()
            clock.tick(60)
    finally:
        pygame.quit()

    # No resolution has been saved by this initial scaffold.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
