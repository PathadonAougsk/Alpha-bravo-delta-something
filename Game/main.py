"""Pygame sketch: a turn-based battle with a JRPG command block.

Usage:
    python main.py --base=50 --enemy=50 --amount=3
"""

import argparse
import math
import sys

import pygame

import assets
from battle import Battle
from command_menu import CommandMenu
from enemy import Enemy
from gunshot import Gunshot
from intro import Intro
from item_flash import ItemFlash
from item_menu import ItemMenu
from determination import Determination
from music import Music
from outro import Outro
from player import Player
from stats import BASE
from textbox import TextBox

WIDTH, HEIGHT = 800, 600
FPS = 12
DETERMINATION_FPS = 48  # the determination box is a dodging game: the
                        # battle can sit at 12 frames, but something you
                        # steer away from bones cannot
BG = (18, 18, 24)
FLOOR = (26, 28, 40)
END_LINGER = 0.4  # a beat after the ending has played out, before the
                  # window closes; the ending sets its own length
HORIZON = 0.45    # where the wall ends and the floor begins

# The wall is zoomed to cover, so there is always more of it than fits: it can
# drift behind the opening without ever showing an edge.
DRIFT_PIXELS = 7.0
DRIFT_SPEED = 0.35
MESSAGE_SLIDE = 0.22  # seconds a new message takes to slide in
# Where the text box sits: across the bottom, wide enough to be the thing you
# are looking at, and stopping short of the HUD panel in the corner.
TALK = (24, 360, 752, 150)
RETRO = 2 # default retro filter: the frame is crunched to 1/N and blown back
           # up. 3 and over starts eating the message strip and the HUD numbers.


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Pygame sketch")
    parser.add_argument(
        "--base",
        type=float,
        default=BASE,
        help=f"baseline the player's stats are scaled from (default: {BASE})",
    )
    parser.add_argument(
        "--enemy",
        type=float,
        default=BASE,
        help=f"baseline each enemy's stats are scaled from (default: {BASE})",
    )
    parser.add_argument(
        "--retro",
        type=int,
        default=RETRO,
        help=f"retro filter: pixels per pixel, 1 turns it off (default: {RETRO})",
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
    if args.retro < 1:
        parser.error("--retro must be 1 or greater")
    return args


def draw_player_bars(surface, font, player, items):
    panel = pygame.Rect(WIDTH - 272, HEIGHT - 86, 260, 74)
    pygame.draw.rect(surface, (24, 30, 58), panel)
    pygame.draw.rect(surface, (90, 120, 210), panel, 2)

    surface.blit(font.render(player.name, True, (235, 238, 255)), (panel.x + 10, panel.y + 8))

    for i, (label, value, shown, cap, color) in enumerate(
        [
            ("HP", player.health, player.shown_health, player.max_health, (90, 210, 130)),
            ("MP", player.mana, player.shown_mana, player.max_mana, (90, 160, 240)),
        ]
    ):
        y = panel.y + 30 + i * 24
        surface.blit(font.render(label, True, (200, 205, 225)), (panel.x + 10, y - 2))
        bar = pygame.Rect(panel.x + 44, y, 140, 12)
        pygame.draw.rect(surface, (40, 44, 60), bar)
        # the pale sliver behind the bar is the change it is still catching up on
        pygame.draw.rect(
            surface,
            tuple(min(255, c + 70) for c in color),
            (bar.x, bar.y, bar.width * shown / cap, bar.height),
        )
        pygame.draw.rect(surface, color, (bar.x, bar.y, bar.width * value / cap, bar.height))
        surface.blit(
            font.render(f"{value}/{cap}", True, (200, 205, 225)), (bar.right + 8, y - 2)
        )

    surface.blit(font.render(f"ITEMS {items}", True, (200, 205, 225)), (panel.right - 86, panel.y + 8))
    if player.guarding:
        surface.blit(font.render("GUARDING", True, (255, 220, 120)), (panel.x + 10, panel.bottom + 4))


def present(screen, frame, pixels):
    """Put the finished frame on screen, through the retro filter if it is on.

    The game draws at full size and the whole frame is crunched down and blown
    back up at the end, so one number controls how chunky everything is -
    sprites, shapes and text alike - and nothing has to know about it.
    """
    if pixels <= 1:
        screen.blit(frame, (0, 0))
        return
    crunched = pygame.transform.scale(frame, (WIDTH // pixels, HEIGHT // pixels))
    pygame.transform.scale(crunched, (WIDTH, HEIGHT), screen)


def ease_out(progress):
    """0 to 1, fast at the start and settling at the end."""
    return 1 - (1 - min(1.0, max(0.0, progress))) ** 3


def draw_message(surface, font, message, age):
    """The message strip, sliding in from the left each time the text changes."""
    landed = ease_out(age / MESSAGE_SLIDE)
    slide = round((1 - landed) * -40)
    text = font.render(message, True, (240, 242, 255))
    strip = pygame.Surface((text.get_width() + 24, text.get_height() + 14), pygame.SRCALPHA)
    strip.fill((12, 14, 24, round(190 * landed)))
    surface.blit(strip, (slide, 6))
    text.set_alpha(round(255 * landed))
    surface.blit(text, (slide + 12, 13))


def main(argv=None, title=None, before_close=None):
    """Run a battle. Returns True on a win, False on a loss, None if quit early."""
    args = parse_args(argv)

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    assets.reset()  # this battle's display, this battle's surfaces
    icon = assets.load(assets.ICON)
    if icon is not None:
        pygame.display.set_icon(icon)
    pygame.display.set_caption(title or f"sketch - battle (player {args.base} / enemy {args.enemy})")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    frame = pygame.Surface((WIDTH, HEIGHT))  # everything is drawn here first
    retro = args.retro

    player = Player((165, HEIGHT - 115), base=args.base)
    enemies = Enemy.formation(args.amount, WIDTH, HEIGHT, base=args.enemy)
    battle = Battle(player, enemies, base=args.base)
    menu = CommandMenu()
    bag = ItemMenu()
    flash = ItemFlash(WIDTH, HEIGHT)
    talk = TextBox()
    gunshot = Gunshot(WIDTH, HEIGHT)
    determination = Determination(WIDTH, HEIGHT)
    intro = Intro(WIDTH, HEIGHT)
    outro = Outro(WIDTH, HEIGHT)
    song = Music()
    song.start()  # loud over the intro, down under the fight by the first turn

    running = True
    end_timer = 0.0
    elapsed = 0.0
    message_age = 0.0
    shown_message = battle.message
    shown_uses = battle.items_used
    while running:
        # the box types, the dodging, the item wipe and the ending all run
        # at the higher rate: they are things you watch moving rather than
        # things you wait on, and glass falling at 12 frames is a slideshow
        smooth = (
            battle.dodging
            or battle.choosing_determination
            or flash.live
            or battle.over
        )
        dt = clock.tick(DETERMINATION_FPS if smooth else FPS) / 1000.0
        elapsed += dt
        song.advance(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pass  # swallowed: the window is closed, not escaped out of
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                retro = 1 if retro > 1 else args.retro  # off, for a clear read
            elif intro.running:
                if event.type == pygame.KEYDOWN:
                    intro.skip()  # any key drops straight into the fight
            elif battle.over:
                if event.type == pygame.KEYDOWN:
                    running = False  # any key skips the result banner
            elif battle.choosing_target:
                # the arrows drive the cursor over the field, not the wheel
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                        battle.move_target(1)
                    elif event.key in (pygame.K_LEFT, pygame.K_UP):
                        battle.move_target(-1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        battle.confirm_target()
                    elif event.key in (pygame.K_BACKSPACE, pygame.K_x):
                        battle.cancel_target()
            elif battle.choosing_item:
                # same arrows, same keys: the bag works like the field cursor
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                        battle.move_item(1)
                    elif event.key in (pygame.K_UP, pygame.K_LEFT):
                        battle.move_item(-1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        battle.confirm_item()
                    elif event.key in (pygame.K_BACKSPACE, pygame.K_x):
                        battle.cancel_item()
            elif battle.choosing_determination:
                # the choices run across the box, so left and right walk them
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                        battle.move_determination(1)
                    elif event.key in (pygame.K_LEFT, pygame.K_UP):
                        battle.move_determination(-1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        # the same key lands the rest of the line first, so a
                        # press while it is still typing cannot pick anything
                        if talk.typed:
                            battle.confirm_determination()
                        else:
                            talk.skip()
                    elif event.key in (pygame.K_BACKSPACE, pygame.K_x):
                        battle.cancel_determination()
            elif battle.accepting_input:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_a:
                    battle.autobattle()
                else:
                    action = menu.handle_event(event)
                    if action:
                        battle.player_command(action)

        if intro.running:
            intro.advance(dt)
        elif battle.watching_cutscene:
            gunshot.advance(dt)
            if gunshot.done:
                battle.finish_cutscene()  # the shot has landed; the fight is lost
        elif battle.dodging:
            # the box runs off held keys rather than presses, so it is handed
            # the keyboard itself instead of the events the rest of the game uses
            if not determination.live:
                determination.begin(player, battle.living_enemies)
            determination.advance(dt, pygame.key.get_pressed())
            if determination.done:
                battle.finish_dodge(determination.survived, determination.taken)
                determination.clear()
        else:
            battle.update(dt)

        if battle.choosing_determination:
            # determination is yours to offer, so you are the one talking: your own
            # face goes in the margin of the box
            if not talk.live:
                talk.say(
                    battle.determination_lines,
                    portrait=assets.PLAYER,
                    options=battle.determination_labels,
                )
            talk.advance(dt)
        elif talk.live:
            talk.close()

        # the field keeps moving whoever's turn it is, so these are driven
        # here rather than from Battle.update, which idles on the player's turn
        player.update(dt)
        for fighter in battle.enemies:
            fighter.update(dt)
        menu.update(dt)

        if battle.items_used != shown_uses:
            shown_uses = battle.items_used
            # the gun takes the screen its own way, so it gets no wipe
            if not battle.watching_cutscene:
                flash.begin()  # out of the middle of the screen
        flash.advance(dt)

        if battle.message != shown_message:
            shown_message, message_age = battle.message, 0.0
        else:
            message_age += dt

        if intro.covering:
            # nothing but the cut-out on black until it reaches its mark
            intro.draw(frame, player)
            present(screen, frame, retro)
            pygame.display.flip()
            continue

        if battle.watching_cutscene:
            # the gun owns the screen outright: no field, no HUD, no message
            gunshot.draw(frame, player)
            present(screen, frame, retro)
            pygame.display.flip()
            continue

        if battle.dodging and determination.covering:
            # the box owns the screen the way the gun does: no field, no HUD
            determination.draw(frame)
            present(screen, frame, retro)
            pygame.display.flip()
            continue

        if battle.over and not intro.running:
            # the fight is decided: the splash takes the screen for a beat,
            # then the window hands back to whoever asked for the battle
            end_timer += dt
            if end_timer >= outro.total + END_LINGER:
                running = False
            outro.draw(frame, battle.result, end_timer)
            present(screen, frame, retro)
            pygame.display.flip()
            continue

        wall = pygame.Rect(0, 0, WIDTH, round(HEIGHT * HORIZON))
        floor = pygame.Rect(0, wall.bottom, WIDTH, HEIGHT - wall.height)
        drift = (0, math.sin(elapsed * DRIFT_SPEED) * DRIFT_PIXELS)
        if not assets.cover(frame, assets.BACKGROUND, wall, drift):
            frame.fill(BG, wall)
        if not assets.tile(frame, assets.FLOOR, floor):
            frame.fill(FLOOR, floor)

        target = battle.target
        for fighter in battle.enemies:  # the beaten ones are still fading out
            fighter.draw(frame, targeted=fighter is target and battle.choosing_target)
        player.draw(frame)

        if battle.accepting_input:
            # high enough that the wheel can swing a label a quarter turn
            # either way without running off the bottom of the screen
            # the wheel greys out whatever the battle will not take this turn
            menu.draw(frame, (player.pos.x + 120, player.pos.y - 90), battle.locked)
        elif battle.choosing_item:
            # the bag opens where the wheel was, so the eye does not have to move
            bag.draw(
                frame,
                (player.pos.x + 120, player.pos.y - 90),
                battle.stock,
                battle.item_index,
            )
        elif battle.choosing_determination:
            # the box is not a panel on the field: it takes the bottom of the
            # screen outright, and the field waits behind it
            talk.draw(frame, TALK, battle.determination_index)

        draw_player_bars(frame, font, player, battle.items)
        if battle.can_autobattle or battle.autobattle_enabled:
            label = "AUTOBATTLE ACTIVE" if battle.autobattle_enabled else "A: AUTOBATTLE"
            frame.blit(font.render(label, True, (255, 220, 120)), (12, HEIGHT - 32))
        draw_message(frame, font, battle.message, message_age)

        if flash.live:
            # the item's wipe, over the finished frame: the HUD it heals goes
            # under the blue with everything else
            flash.draw(frame)

        if battle.dodging:
            # the last beat of the box: the black it left falls off the
            # battle in panes, which have to go over the finished frame
            determination.draw(frame)

        if intro.running:
            intro.draw(frame, player)  # the black lifting off the finished frame

        # the item wipe winds the retro filter up and back down with it, so
        # the heal blocks the screen up and it comes back into focus after
        present(screen, frame, flash.crunch(retro))
        pygame.display.flip()

    song.stop()
    try:
        if before_close is not None:
            before_close()
    finally:
        pygame.quit()
    return battle.result


if __name__ == "__main__":
    # True = won, False = lost, None = quit before the fight ended
    sys.exit(0 if main() is not False else 1)
