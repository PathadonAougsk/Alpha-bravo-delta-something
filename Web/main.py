"""Pygame sketch: a turn-based battle with a JRPG command block.

Usage:
    python main.py --base=50 --enemy=50 --amount=3
"""

import argparse
import sys

import pygame

from battle import Battle
from command_menu import CommandMenu
from enemy import Enemy
from player import Player
from stats import BASE

WIDTH, HEIGHT = 960, 600
FPS = 60
BG = (18, 18, 24)
FLOOR = (26, 28, 40)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Pygame sketch")
    parser.add_argument(
        "--base",
        type=int,
        default=BASE,
        help=f"baseline the player's stats are scaled from (default: {BASE})",
    )
    parser.add_argument(
        "--enemy",
        type=int,
        default=BASE,
        help=f"baseline each enemy's stats are scaled from (default: {BASE})",
    )
    parser.add_argument(
        "--amount",
        type=int,
        default=3,
        help="how many enemies to fight (default: 3)",
    )
    args = parser.parse_args(argv)
    if args.base < 1:
        parser.error("--base must be 1 or greater")
    if args.enemy < 1:
        parser.error("--enemy must be 1 or greater")
    if args.amount < 0:
        parser.error("--amount must be 0 or greater")
    return args


def draw_player_bars(surface, font, player, items):
    panel = pygame.Rect(12, HEIGHT - 86, 300, 74)
    pygame.draw.rect(surface, (24, 30, 58), panel, border_radius=6)
    pygame.draw.rect(surface, (90, 120, 210), panel, 2, border_radius=6)

    surface.blit(font.render(player.name, True, (235, 238, 255)), (panel.x + 10, panel.y + 8))

    for i, (label, value, cap, color) in enumerate(
        [
            ("HP", player.health, player.max_health, (90, 210, 130)),
            ("MP", player.mana, player.max_mana, (90, 160, 240)),
        ]
    ):
        y = panel.y + 30 + i * 24
        surface.blit(font.render(label, True, (200, 205, 225)), (panel.x + 10, y - 2))
        bar = pygame.Rect(panel.x + 44, y, 180, 12)
        pygame.draw.rect(surface, (40, 44, 60), bar)
        pygame.draw.rect(surface, color, (bar.x, bar.y, bar.width * value / cap, bar.height))
        surface.blit(
            font.render(f"{value}/{cap}", True, (200, 205, 225)), (bar.right + 8, y - 2)
        )

    surface.blit(font.render(f"ITEMS {items}", True, (200, 205, 225)), (panel.right + 14, panel.y + 28))
    if player.guarding:
        surface.blit(font.render("GUARDING", True, (255, 220, 120)), (panel.right + 14, panel.y + 52))


def main(argv=None):
    """Run a battle. Returns True on a win, False on a loss, None if quit early."""
    args = parse_args(argv)

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"sketch - battle (player {args.base} / enemy {args.enemy})")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    big_font = pygame.font.SysFont(None, 64, bold=True)

    player = Player((190, HEIGHT - 190), base=args.base)
    enemies = Enemy.formation(args.amount, WIDTH, HEIGHT, base=args.enemy)
    battle = Battle(player, enemies, base=args.base)
    menu = CommandMenu()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif battle.accepting_input:
                action = menu.handle_event(event)
                if action:
                    battle.player_command(action)

        battle.update(dt)

        screen.fill(BG)
        pygame.draw.rect(screen, FLOOR, (0, HEIGHT * 0.45, WIDTH, HEIGHT * 0.55))

        target = battle.target
        for enemy in battle.living_enemies:
            enemy.draw(screen, targeted=enemy is target and battle.accepting_input)
        player.draw(screen)

        if battle.accepting_input:
            menu.draw(screen, (player.pos.x + 110, player.pos.y + 14))

        draw_player_bars(screen, font, player, battle.items)
        screen.blit(font.render(battle.message, True, (225, 228, 245)), (12, 16))

        if battle.over:
            banner = big_font.render(
                "VICTORY" if battle.result else "DEFEAT", True, (255, 235, 140)
            )
            screen.blit(banner, banner.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 40)))

        pygame.display.flip()

    pygame.quit()
    return battle.result


if __name__ == "__main__":
    # True = won, False = lost, None = quit before the fight ended
    sys.exit(0 if main() is not False else 1)
