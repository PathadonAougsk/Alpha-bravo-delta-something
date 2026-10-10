"""Battle behavior checks; run with python -m unittest discover -s tests."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Game"))

from battle import BEAT, DEFEAT, ENEMY_TURN, PLAYER_TURN, RESOLVING, VICTORY, Battle
from command_menu import ATTACK, GUARD, ITEM
from entity import Entity


class AutobattleTests(unittest.TestCase):
    def setUp(self):
        # Keep damage deterministic while exercising the normal attack path.
        critical = patch("entity.random.random", return_value=1.0)
        spread = patch("entity.random.uniform", return_value=1.0)
        critical.start()
        spread.start()
        self.addCleanup(critical.stop)
        self.addCleanup(spread.stop)
        self.player = Entity((0, 0), health=100, attack_damage=10)
        self.enemy = Entity((1, 0), health=30, attack_damage=5)
        self.battle = Battle(self.player, [self.enemy])

    def finish_round(self):
        self.battle.update(BEAT)  # finish the player attack
        self.battle.update(BEAT)  # enemy attacks
        self.battle.update(BEAT)  # return to the player

    def test_start_attacks_immediately_and_keeps_normal_turn_timing(self):
        self.assertTrue(self.battle.autobattle())
        self.assertFalse(self.battle.accepting_input)
        self.assertEqual(self.enemy.health, 20)
        self.assertEqual(self.battle.state, RESOLVING)
        self.battle.update(BEAT / 2)
        self.assertEqual(self.player.health, 100)
        self.battle.update(BEAT / 2)
        self.assertEqual(self.battle.state, ENEMY_TURN)
        self.battle.update(BEAT)
        self.assertEqual(self.player.health, 95)
        self.battle.update(BEAT)
        self.assertEqual(self.battle.state, PLAYER_TURN)
        self.battle.update(0)
        self.assertEqual(self.enemy.health, 10)
        self.assertEqual(self.battle.items, 3)
        self.assertFalse(self.player.guarding)

    def test_auto_retargets_and_stops_after_victory(self):
        self.enemy.health = 10
        second = Entity((2, 0), health=10, attack_damage=5)
        self.battle.enemies.append(second)
        self.battle.autobattle()
        self.finish_round()
        self.assertEqual(self.player.health, 95)  # only the survivor attacks
        self.battle.update(0)
        self.assertEqual(second.health, 0)
        self.battle.update(BEAT)
        self.assertEqual(self.battle.state, VICTORY)
        self.assertTrue(self.battle.result)
        self.battle.update(BEAT)
        self.assertEqual(self.player.health, 95)

    def test_auto_stops_after_defeat(self):
        self.player.health = 5
        self.battle.autobattle()
        self.finish_round()
        self.assertEqual(self.battle.state, DEFEAT)
        self.assertFalse(self.battle.result)
        self.battle.update(BEAT)
        self.assertEqual(self.enemy.health, 20)

    def test_manual_commands_close_the_first_turn_activation_window(self):
        for action in (ATTACK, GUARD, ITEM):
            with self.subTest(action=action):
                self.battle = Battle(self.player, [self.enemy])
                self.battle.player_command(action)
                self.assertFalse(self.battle.autobattle())
                self.finish_round()
                self.assertTrue(self.battle.accepting_input)
                self.assertFalse(self.battle.autobattle())

    def test_unused_turn_still_allows_activation(self):
        self.battle.items = 0
        self.battle.player_command(ITEM)
        self.battle.player_command("unknown")
        self.assertTrue(self.battle.can_autobattle)
        self.assertTrue(self.battle.autobattle())

    def test_manual_input_and_reactivation_do_not_interrupt_auto(self):
        self.battle.autobattle()
        self.assertFalse(self.battle.autobattle())
        self.finish_round()
        self.battle.player_command(ITEM)
        self.assertEqual(self.battle.items, 3)
        self.battle.update(0)
        self.assertEqual(self.enemy.health, 10)

    def test_finished_battle_cannot_activate_and_new_battle_starts_manual(self):
        empty = Battle(self.player, [])
        self.assertFalse(empty.autobattle())
        self.battle.autobattle()
        fresh = Battle(self.player, [self.enemy])
        self.assertFalse(fresh.autobattle_enabled)
        self.assertTrue(fresh.can_autobattle)


if __name__ == "__main__":
    unittest.main()
