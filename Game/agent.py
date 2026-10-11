"""Paused, standalone agent battles using the same combat and dodge engines."""

from collections import defaultdict
from contextlib import contextmanager
import io
import math
import os
import random
import threading

import pygame

import assets
from battle import BEAT, Battle
from command_menu import ATTACK, DETERMINATION, GUARD, ITEM
from determination import Blaster, Determination, SOUL_HIT, SOUL_SPEED
from enemy import Enemy
from items import GUN, HEALTH, ORDER
from player import Player

WIDTH, HEIGHT = 800, 600
STEP = 1 / 48
MAX_ENEMIES = 10
MAX_BASE = 10000
RANDOM_LOCK = threading.RLock()
DIRECTIONS = {
    "still": (),
    "left": (pygame.K_LEFT,),
    "right": (pygame.K_RIGHT,),
    "up": (pygame.K_UP,),
    "down": (pygame.K_DOWN,),
    "up_left": (pygame.K_UP, pygame.K_LEFT),
    "up_right": (pygame.K_UP, pygame.K_RIGHT),
    "down_left": (pygame.K_DOWN, pygame.K_LEFT),
    "down_right": (pygame.K_DOWN, pygame.K_RIGHT),
}


class AgentBattle:
    """A battle whose clock advances only when the agent takes an action."""

    def __init__(self, base=50, enemy_base=168, amount=1, seed=None):
        for label, value in (("base", base), ("enemy_base", enemy_base)):
            if not math.isfinite(value) or not 1 <= value <= MAX_BASE:
                raise ValueError(f"{label} must be finite and between 1 and {MAX_BASE}.")
        if isinstance(amount, bool) or not isinstance(amount, int) or not 0 <= amount <= MAX_ENEMIES:
            raise ValueError(f"amount must be an integer between 0 and {MAX_ENEMIES}.")
        self.seed = seed
        self.rng = random.Random(seed)
        self.abandoned = False
        self.turns = 0
        self.events = []
        self.wave = Determination(WIDTH, HEIGHT)
        with self.random_context():
            player = Player((WIDTH * 0.2, HEIGHT * 0.73), base=base)
            enemies = Enemy.formation(amount, WIDTH, HEIGHT, base=enemy_base)
            # Agent turns must remain manual even when the window game defaults
            # to automatic battles. Preserve that default for existing callers.
            self.battle = Battle(player, enemies, base=base, autobattle=False)
            if not self.battle.over:
                self.battle.message = "Choose an action from available_actions."

    @contextmanager
    def random_context(self):
        """Isolate the engine's module-level random calls per session."""
        with RANDOM_LOCK:
            previous = random.getstate()
            random.setstate(self.rng.getstate())
            try:
                yield
            finally:
                self.rng.setstate(random.getstate())
                random.setstate(previous)

    def _require_active(self):
        if self.abandoned or self.battle.over:
            raise ValueError("Battle is finished; start a new battle to play again.")

    def _record(self):
        if not self.events or self.events[-1] != self.battle.message:
            self.events.append(self.battle.message)

    def act(self, action, target=0):
        """Spend one player turn, then resolve every enemy's response."""
        self._require_active()
        battle = self.battle
        if not battle.accepting_input:
            raise ValueError("The dodge wave owns the turn; use dodge_step.")
        if action not in self.available_actions():
            raise ValueError(f"Action {action!r} is unavailable; inspect available_actions.")
        if action == ATTACK:
            if isinstance(target, bool) or not isinstance(target, int) or not 0 <= target < len(battle.enemies):
                raise ValueError("target must be an enemy's integer id from the observation.")
            if not battle.enemies[target].alive:
                raise ValueError("That enemy is already defeated.")

        with self.random_context():
            self.events = []
            if action == ATTACK:
                battle.player_command(ATTACK)
                living = battle.living_enemies
                battle.move_target(living.index(battle.enemies[target]) - living.index(battle.target))
                battle.confirm_target()
            elif action == GUARD:
                battle.player_command(GUARD)
            elif action in (HEALTH, GUN):
                battle.player_command(ITEM)
                battle.move_item(ORDER.index(action) - battle.item_index)
                battle.confirm_item()
            else:
                battle.player_command(DETERMINATION)
                if action == "flee":
                    battle.move_determination(1)
                battle.confirm_determination()
            self.turns += 1
            self._record()

            if battle.watching_cutscene:
                # Presentation is skipped; the gun's real outcome is defeat.
                battle.finish_cutscene()
                self._record()
            elif battle.dodging:
                self.wave.begin(battle.player, battle.living_enemies)
                # The visual game creates this RNG independently of the global
                # one. Seed it explicitly to make agent replays reproducible.
                self.wave.rolls.seed(random.getrandbits(64))
            else:
                # One resolving step, each enemy, then the return to the player.
                for _ in range(len(battle.enemies) + 2):
                    if battle.over or battle.accepting_input:
                        break
                    battle.update(BEAT)
                    self._record()
                if not battle.over and not battle.accepting_input:
                    raise RuntimeError("Battle did not finish its round.")
            # Let HP bars catch up without advancing combat or the wave.
            battle.player.update(1)
            for enemy in battle.enemies:
                enemy.update(1)
        return self.observe()

    def dodge_step(self, direction="still", frames=6):
        """Hold a direction for 1–48 simulated frames at the game's 48 FPS."""
        self._require_active()
        if not self.battle.dodging:
            raise ValueError("No dodge wave is active; choose spare when it is available.")
        if direction not in DIRECTIONS:
            raise ValueError("Unknown direction.")
        if isinstance(frames, bool) or not isinstance(frames, int) or not 1 <= frames <= 48:
            raise ValueError("frames must be an integer between 1 and 48.")
        keys = defaultdict(bool, {key: True for key in DIRECTIONS[direction]})
        with self.random_context():
            self.events = []
            before = self.battle.player.health
            for _ in range(frames):
                self.wave.advance(STEP, keys)
                self.battle.player.update(STEP)
                if self.wave.done:
                    self.battle.finish_dodge(self.wave.survived, self.wave.taken)
                    self.wave.clear()
                    self._record()
                    break
            if self.battle.player.health < before:
                self.events.insert(0, f"Wave dealt {before - self.battle.player.health} damage.")
        return self.observe()

    def available_actions(self):
        """Return legal turn actions for the current observation."""
        if self.abandoned or not self.battle.accepting_input or self.battle.over:
            return []
        actions = [ATTACK, GUARD]
        actions.extend(item for item in ORDER if self.battle.stock[item] > 0)
        if self.battle.determination_ready:
            actions.extend(("spare", "flee"))
        return actions

    def observe(self):
        """Return JSON-compatible combat state and currently visible hazards."""
        battle = self.battle

        def fighter(entity):
            return {
                "name": entity.name,
                "health": entity.health,
                "max_health": entity.max_health,
                "mana": entity.mana,
                "max_mana": entity.max_mana,
                "attack_damage": entity.attack_damage,
                "alive": entity.alive,
                "guarding": entity.guarding,
            }

        observation = {
            "state": "abandoned" if self.abandoned else battle.state,
            "result": None if self.abandoned else battle.result,
            "turns": self.turns,
            "seed": self.seed,
            "message": "Battle abandoned." if self.abandoned else battle.message,
            "events": list(self.events),
            "player": fighter(battle.player),
            "enemies": [dict(fighter(enemy), id=i, recovering=enemy.recovering)
                        for i, enemy in enumerate(battle.enemies)],
            "inventory": dict(battle.stock),
            "heal_amount": battle.item_heal,
            "available_actions": self.available_actions(),
            "dodge": None,
        }
        if battle.dodging and not self.abandoned:
            wave = self.wave
            hazards = []
            for shot in wave.shots:
                rect = shot.rect
                hazard = {
                    "kind": "blaster" if isinstance(shot, Blaster) else "pellet" if shot.pellet else "bone",
                    "rect": list(rect),
                    "live": shot.live,
                    "blue": shot.blue,
                    "warning_seconds": round(max(0, shot.tell), 4),
                }
                if isinstance(shot, Blaster):
                    hazard.update(axis="horizontal" if shot.across else "vertical",
                                  burn_seconds=round(max(0, shot.burn), 4))
                else:
                    hazard["velocity"] = list(shot.drift)
                hazards.append(hazard)
            observation["dodge"] = {
                "phase": wave.phase,
                "phase_seconds": round(wave.beat, 4),
                "wave_seconds": wave.length,
                "box": list(wave.box()),
                "heart": list(wave.heart),
                "hitbox_half_size": SOUL_HIT,
                "speed": SOUL_SPEED,
                "invulnerable_seconds": round(wave.grace, 4),
                "damage_per_hit": wave.bite,
                "damage_taken": wave.taken,
                "blue_wall_present": wave.blue_up,
                "hazards": hazards,
            }
        return observation

    def quit(self):
        """Abandon without recording a victory or defeat."""
        self.abandoned = True
        self.events = ["Battle abandoned."]
        self.wave.clear()
        return self.observe()

    def screenshot(self):
        """Render an agent view with game sprites, HUD and the actual dodge box."""
        with self.random_context():
            if not pygame.display.get_init():
                os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
                pygame.display.init()
            if pygame.display.get_surface() is None:
                pygame.display.set_mode((1, 1))
            pygame.font.init()
            surface = pygame.Surface((WIDTH, HEIGHT))
            wall = pygame.Rect(0, 0, WIDTH, 270)
            floor = pygame.Rect(0, 270, WIDTH, HEIGHT - 270)
            if not assets.cover(surface, assets.BACKGROUND, wall):
                surface.fill((18, 18, 24), wall)
            if not assets.tile(surface, assets.FLOOR, floor):
                surface.fill((26, 28, 40), floor)
            self.battle.player.draw(surface)
            for enemy in self.battle.enemies:
                enemy.draw(surface)
            font = assets.font(22)
            player = self.battle.player
            labels = [
                f"{self.observe()['state'].upper()} | turn {self.turns}",
                f"HP {player.health}/{player.max_health} | HEALTH {self.battle.stock[HEALTH]} | GUN {self.battle.stock[GUN]}",
                "Actions: " + ", ".join(self.available_actions()),
                self.observe()["message"],
            ]
            for i, label in enumerate(labels):
                surface.blit(font.render(label, True, (255, 255, 255)), (16, 485 + i * 26))
            if self.battle.dodging and not self.abandoned:
                # Death fragments are lazily generated by draw(). Keep their
                # cosmetic random choices out of the wave's gameplay RNG.
                wave_random = self.wave.rolls.getstate()
                try:
                    self.wave.draw(surface)
                finally:
                    self.wave.rolls.setstate(wave_random)
            output = io.BytesIO()
            pygame.image.save(surface, output, "battle.png")
            return output.getvalue()
