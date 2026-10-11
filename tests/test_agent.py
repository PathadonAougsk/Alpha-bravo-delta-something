"""Agent gameplay checks; run with python -m unittest discover -s tests."""

import io
import math
import os
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Game"))

import pygame

from agent import AgentBattle
from battle import Battle
from determination import DODGING, Shot


class AgentBattleTests(unittest.TestCase):
    def test_manual_override_preserves_keyboard_default(self):
        with patch("battle.ALWAYS_AUTOBATTLE", True):
            session = AgentBattle(seed=1)
            self.assertTrue(session.battle.accepting_input)
            keyboard = Battle(session.battle.player, session.battle.enemies)
            self.assertTrue(keyboard.autobattle_enabled)

    def test_bad_setup_rejected(self):
        for options in (
            {"base": 0}, {"base": math.nan}, {"base": math.inf},
            {"enemy_base": 10001}, {"amount": -1}, {"amount": 11},
            {"amount": 1.5}, {"amount": True},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                AgentBattle(**options)

    def test_zero_enemies_is_immediate_victory(self):
        session = AgentBattle(amount=0)
        self.assertIs(session.observe()["result"], True)
        self.assertEqual(session.observe()["available_actions"], [])

    def test_reading_does_not_advance_and_random_state_is_isolated(self):
        before_random = random.getstate()
        session = AgentBattle(seed=42)
        before = session.observe()
        self.assertEqual(session.observe(), before)
        self.assertEqual(random.getstate(), before_random)
        session.act("attack")
        self.assertEqual(random.getstate(), before_random)

    def test_one_action_resolves_all_living_enemies(self):
        session = AgentBattle(enemy_base=50, amount=3, seed=1)
        with patch("entity.random.uniform", return_value=1), patch("entity.random.random", return_value=1):
            before = session.observe()
            after = session.act("attack", target=2)
        self.assertEqual(after["state"], "player")
        self.assertEqual(after["turns"], 1)
        self.assertEqual(after["enemies"][2]["health"],
                         before["enemies"][2]["health"] - before["player"]["attack_damage"])
        incoming = sum(enemy["attack_damage"] for enemy in after["enemies"] if enemy["alive"])
        self.assertEqual(after["player"]["health"], before["player"]["health"] - incoming)
        self.assertEqual(len(after["events"]), 5)  # player, three HEADs, your move

    def test_target_ids_stay_stable_and_victory_stops_play(self):
        session = AgentBattle(enemy_base=1, amount=2, seed=7)
        after = session.act("attack", target=0)
        self.assertFalse(after["enemies"][0]["alive"])
        before = session.observe()
        with self.assertRaises(ValueError):
            session.act("attack", target=0)
        self.assertEqual(session.observe(), before)
        after = session.act("attack", target=1)
        self.assertEqual(after["state"], "victory")
        self.assertIs(after["result"], True)
        with self.assertRaises(ValueError):
            session.act("guard")

    def test_invalid_action_and_target_cost_nothing(self):
        session = AgentBattle(seed=1)
        for action, target in (("spare", 0), ("unknown", 0), ("attack", -1),
                               ("attack", 2), ("attack", 0.5), ("attack", True)):
            before = session.observe()
            with self.subTest(action=action, target=target), self.assertRaises(ValueError):
                session.act(action, target)
            self.assertEqual(session.observe(), before)

    def test_guard_topples_and_recovery_costs_next_enemy_turn(self):
        session = AgentBattle(seed=1)
        session.battle.fizzle = 1
        after = session.act("guard")
        self.assertEqual(after["player"]["health"], after["player"]["max_health"])
        self.assertTrue(after["enemies"][0]["recovering"])
        after = session.act("attack")
        self.assertEqual(after["player"]["health"], after["player"]["max_health"])
        self.assertFalse(after["enemies"][0]["recovering"])
        self.assertTrue(any("picks itself back up" in event for event in after["events"]))

    def test_guard_halves_real_incoming_damage(self):
        session = AgentBattle(seed=1)
        session.battle.fizzle = 0
        before = session.observe()
        with patch("entity.random.uniform", return_value=1), patch("entity.random.random", return_value=1):
            after = session.act("guard")
        self.assertEqual(after["player"]["health"],
                         before["player"]["health"] - max(1, before["enemies"][0]["attack_damage"] // 2))
        self.assertFalse(after["player"]["guarding"])

    def test_health_heals_and_enemies_still_respond(self):
        session = AgentBattle(seed=1)
        session.battle.player.health = 40
        with patch("entity.random.uniform", return_value=1), patch("entity.random.random", return_value=1):
            after = session.act("health")
        self.assertEqual(after["player"]["health"], 40 + after["heal_amount"] - after["enemies"][0]["attack_damage"])
        self.assertEqual(after["inventory"]["health"], 2)
        session.battle.stock["health"] = 0
        before = session.observe()
        with self.assertRaises(ValueError):
            session.act("health")
        self.assertEqual(session.observe(), before)

    def test_gun_is_defeat_and_quit_has_no_result(self):
        session = AgentBattle(seed=1)
        after = session.act("gun")
        self.assertEqual(after["state"], "defeat")
        self.assertIs(after["result"], False)
        self.assertEqual(after["player"]["health"], 0)
        self.assertEqual(after["inventory"]["gun"], 0)
        abandoned = AgentBattle(seed=1).quit()
        self.assertEqual(abandoned["state"], "abandoned")
        self.assertIsNone(abandoned["result"])
        self.assertEqual(abandoned["available_actions"], [])

    def test_flee_does_not_escape(self):
        session = AgentBattle(seed=1)
        session.battle.player.health = 50
        after = session.act("flee")
        self.assertEqual(after["state"], "player")
        self.assertLess(after["player"]["health"], 50)
        self.assertEqual(after["enemies"][0]["health"], after["enemies"][0]["max_health"])

    def start_wave(self, enemy_base=1):
        session = AgentBattle(enemy_base=enemy_base, seed=1)
        session.battle.player.health = session.battle.player.max_health // 2
        after = session.act("spare")
        self.assertEqual(after["state"], "dodging")
        self.assertEqual(after["dodge"]["phase"], "opening")
        return session

    def test_wave_survival_restores_hp_and_returns_turn(self):
        session = self.start_wave()
        with self.assertRaises(ValueError):
            session.act("attack")
        for _ in range(12):
            after = session.dodge_step("still", 48)
            if after["state"] != "dodging":
                break
        self.assertEqual(after["state"], "player")
        self.assertEqual(after["player"]["health"], after["player"]["max_health"])
        self.assertIsNone(after["dodge"])

    def test_wave_movement_and_blue_collision_use_actual_engine(self):
        session = self.start_wave()
        session.dodge_step("still", 20)
        self.assertEqual(session.wave.phase, DODGING)
        before = session.observe()["dodge"]["heart"]
        after = session.dodge_step("right", 6)
        self.assertAlmostEqual(after["dodge"]["heart"][0], before[0] + 285 * 6 / 48)
        session.wave.shots = [Shot(session.wave.heart, (0, 0), (80, 80), blue=True)]
        before_hp = session.battle.player.health
        session.dodge_step("still", 1)
        self.assertEqual(session.battle.player.health, before_hp)
        after = session.dodge_step("left", 1)
        self.assertLess(after["player"]["health"], before_hp)

    def test_wave_death_is_defeat(self):
        session = self.start_wave(enemy_base=10000)
        session.dodge_step("still", 20)
        session.wave.shots = [Shot(session.wave.heart, (0, 0), (40, 40))]
        session.dodge_step("still", 1)
        for _ in range(3):
            after = session.dodge_step("still", 48)
            if after["state"] != "dodging":
                break
        self.assertEqual(after["state"], "defeat")
        self.assertIs(after["result"], False)

    def test_invalid_dodge_call_does_not_advance(self):
        session = AgentBattle(seed=1)
        with self.assertRaises(ValueError):
            session.dodge_step()
        session = self.start_wave()
        for direction, frames in (("unknown", 6), ("still", 0), ("still", 49),
                                   ("still", 1.5), ("still", True)):
            before = session.observe()
            with self.assertRaises(ValueError):
                session.dodge_step(direction, frames)
            self.assertEqual(session.observe(), before)

    def test_seed_replays_combat_and_wave_despite_other_sessions(self):
        first, second = AgentBattle(seed=7), AgentBattle(seed=7)
        self.assertEqual(first.observe(), second.observe())
        first.act("attack")
        AgentBattle(seed=99).act("guard")
        second.act("attack")
        self.assertEqual(first.observe(), second.observe())
        for session in (first, second):
            session.battle.player.health = 40
            session.act("spare")
        for _ in range(7):
            first.dodge_step("still", 12)
            AgentBattle(seed=100).act("attack")
            second.dodge_step("still", 12)
            self.assertEqual(first.observe(), second.observe())

    def test_screenshot_is_png_and_does_not_change_gameplay(self):
        session = AgentBattle(seed=1)
        before = session.observe()
        random_before = random.getstate()
        png = session.screenshot()
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(pygame.image.load(io.BytesIO(png)).get_size(), (800, 600))
        self.assertEqual(session.observe(), before)
        self.assertEqual(random.getstate(), random_before)
        session = self.start_wave()
        session.dodge_step("still", 48)
        before = session.observe()
        wave_rng = session.wave.rolls.getstate()
        session.screenshot()
        self.assertEqual(session.observe(), before)
        self.assertEqual(session.wave.rolls.getstate(), wave_rng)


if __name__ == "__main__":
    unittest.main()
