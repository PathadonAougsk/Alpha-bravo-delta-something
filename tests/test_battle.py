"""Battle behavior checks; run with python -m unittest discover -s tests."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Game"))

from battle import (
    BEAT,
    DEFEAT,
    ENEMY_TURN,
    FLEE,
    DETERMINATION_LINES,
    DETERMINATION_LINES_LOW,
    PLAYER_TURN,
    RESOLVING,
    SPARE,
    VICTORY,
    Battle,
)
from command_menu import ATTACK, GUARD, ITEM, DETERMINATION
from entity import Entity
from items import GUN, HEALTH
from determination import Determination, Shot


class Fighter(Entity):
    """An enemy stand-in: the battle reads the recovery flag Enemy carries."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recovering = False


class AutobattleTests(unittest.TestCase):
    def setUp(self):
        # Keep damage deterministic while exercising the normal attack path.
        critical = patch("entity.random.random", return_value=1.0)
        spread = patch("entity.random.uniform", return_value=1.0)
        # and keep the guard from turning a swing aside on its own
        fizzle = patch("battle.random.random", return_value=1.0)
        critical.start()
        spread.start()
        fizzle.start()
        self.addCleanup(critical.stop)
        self.addCleanup(spread.stop)
        self.addCleanup(fizzle.stop)
        self.player = Entity((0, 0), health=100, attack_damage=10)
        self.enemy = Fighter((1, 0), health=30, attack_damage=5)
        self.battle = Battle(self.player, [self.enemy])

    def finish_round(self):
        self.battle.update(BEAT)  # finish the player attack
        self.battle.update(BEAT)  # enemy attacks
        self.battle.update(BEAT)  # return to the player

    def spend_turn(self, action):
        """Run `action` through to the press that actually costs the turn.

        ATTACK opens the field cursor and ITEM opens the bag; neither spends
        the turn until it is confirmed.
        """
        self.battle.player_command(action)
        if action == ATTACK:
            self.battle.confirm_target()
        elif action == ITEM:
            self.battle.confirm_item()

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
        self.assertEqual(self.battle.stock[HEALTH], 3)
        self.assertFalse(self.player.guarding)

    def test_auto_retargets_and_stops_after_victory(self):
        self.enemy.health = 10
        second = Fighter((2, 0), health=10, attack_damage=5)
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
                self.spend_turn(action)
                self.assertFalse(self.battle.autobattle())
                self.finish_round()
                self.assertTrue(self.battle.accepting_input)
                self.assertFalse(self.battle.autobattle())

    def test_unused_turn_still_allows_activation(self):
        self.battle.stock = {HEALTH: 0, GUN: 0}
        self.battle.player_command(ITEM)
        self.battle.player_command("unknown")
        self.assertTrue(self.battle.can_autobattle)
        self.assertTrue(self.battle.autobattle())

    def test_manual_input_and_reactivation_do_not_interrupt_auto(self):
        self.battle.autobattle()
        self.assertFalse(self.battle.autobattle())
        self.finish_round()
        self.battle.player_command(ITEM)
        self.assertEqual(self.battle.stock[HEALTH], 3)
        self.battle.update(0)
        self.assertEqual(self.enemy.health, 10)

    def test_finished_battle_cannot_activate_and_new_battle_starts_manual(self):
        empty = Battle(self.player, [])
        self.assertFalse(empty.autobattle())
        self.battle.autobattle()
        fresh = Battle(self.player, [self.enemy])
        self.assertFalse(fresh.autobattle_enabled)
        self.assertTrue(fresh.can_autobattle)

    @patch("battle.ALWAYS_AUTOBATTLE", True)
    def test_override_starts_each_battle_on_update_and_keeps_attacking(self):
        for _ in range(2):
            with self.subTest(battle=_):
                self.player = Entity((0, 0), health=100, attack_damage=10)
                self.enemy = Fighter((1, 0), health=30, attack_damage=5)
                self.battle = Battle(self.player, [self.enemy])
                self.assertTrue(self.battle.autobattle_enabled)
                self.assertFalse(self.battle.accepting_input)
                self.assertEqual(self.enemy.health, 30)
                self.battle.player_command(GUARD)
                self.assertFalse(self.player.guarding)
                self.battle.update(0)
                self.assertEqual(self.enemy.health, 20)
                self.finish_round()
                self.assertEqual(self.player.health, 95)
                self.battle.update(0)
                self.assertEqual(self.enemy.health, 10)

    @patch("battle.ALWAYS_AUTOBATTLE", True)
    def test_override_leaves_empty_battle_finished_without_attacking(self):
        empty = Battle(self.player, [])
        empty.update(BEAT)
        self.assertEqual(empty.state, VICTORY)
        self.assertFalse(empty.autobattle_enabled)
        self.assertEqual(self.player.health, 100)


class DeterminationChoiceTests(unittest.TestCase):
    """DETERMINATION opens the text box; what determination means is the second question."""

    def setUp(self):
        self.player = Entity((0, 0), health=100, attack_damage=10)
        self.enemy = Fighter((1, 0), health=30, attack_damage=5)
        self.battle = Battle(self.player, [self.enemy])

    def open_box(self):
        """Get hurt enough for DETERMINATION to unlock, and pick it."""
        self.player.health = 40
        self.battle.player_command(DETERMINATION)

    def test_determination_stays_shut_while_you_are_standing_comfortably(self):
        self.battle.player_command(DETERMINATION)
        self.assertFalse(self.battle.choosing_determination)
        self.assertEqual(self.battle.state, PLAYER_TURN)
        self.assertTrue(self.battle.can_autobattle)  # the press cost nothing

    def test_opening_the_box_offers_both_ways_out(self):
        self.open_box()
        self.assertTrue(self.battle.choosing_determination)
        self.assertEqual(self.battle.determination_labels, ["Spare", "Flee"])
        self.assertEqual(self.battle.determination_option, SPARE)
        self.assertEqual(self.battle.determination_index, 0)

    def test_the_pick_walks_the_choices_and_wraps_round(self):
        self.open_box()
        self.battle.move_determination(1)
        self.assertEqual(self.battle.determination_option, FLEE)
        self.battle.move_determination(1)
        self.assertEqual(self.battle.determination_option, SPARE)
        self.battle.move_determination(-1)
        self.assertEqual(self.battle.determination_option, FLEE)

    def test_backing_out_does_not_spend_the_turn(self):
        self.open_box()
        self.battle.cancel_determination()
        self.assertEqual(self.battle.state, PLAYER_TURN)
        self.assertTrue(self.battle.can_autobattle)

    def test_sparing_hands_the_screen_to_the_dodging_box(self):
        self.open_box()
        self.battle.confirm_determination()
        self.assertTrue(self.battle.dodging)
        self.assertFalse(self.battle.can_autobattle)

    def test_running_spends_the_turn_finding_out_there_is_nowhere_to_run(self):
        self.open_box()
        self.battle.move_determination(1)
        self.battle.confirm_determination()
        self.assertEqual(self.battle.state, RESOLVING)
        self.assertEqual(self.enemy.health, 30)  # nothing was swung at

    def test_the_box_stops_narrating_once_there_is_almost_nothing_left(self):
        self.open_box()
        self.assertEqual(self.battle.determination_lines, DETERMINATION_LINES)
        self.player.health = 20
        self.assertEqual(self.battle.determination_lines, DETERMINATION_LINES_LOW)

    def test_the_choices_do_nothing_while_the_box_is_shut(self):
        self.battle.move_determination(1)
        self.battle.confirm_determination()
        self.battle.cancel_determination()
        self.assertEqual(self.battle.determination_index, 0)
        self.assertEqual(self.battle.state, PLAYER_TURN)


class DeterminationWaveTests(unittest.TestCase):
    """What the wave costs, and what living through it pays."""

    def setUp(self):
        self.player = Entity((0, 0), health=100, attack_damage=10)
        self.player.health = 30  # hurt enough for DETERMINATION to open
        self.enemy = Fighter((1, 0), health=30, attack_damage=5)
        self.battle = Battle(self.player, [self.enemy])
        self.battle.player_command(DETERMINATION)
        self.battle.confirm_determination()

    def test_living_through_it_hands_back_the_turn_and_the_whole_bar(self):
        self.battle.finish_dodge(True, taken=12)
        self.assertEqual(self.player.health, self.player.max_health)
        self.assertEqual(self.battle.state, PLAYER_TURN)
        self.assertFalse(self.player.guarding)

    def test_the_bar_comes_back_even_from_a_wave_that_never_landed_one(self):
        self.battle.finish_dodge(True, taken=0)
        self.assertEqual(self.player.health, self.player.max_health)
        self.assertIn("70", self.battle.message)

    def test_dying_in_it_is_still_defeat(self):
        self.player.health = 0
        self.battle.finish_dodge(False, taken=30)
        self.assertEqual(self.battle.state, DEFEAT)
        self.assertEqual(self.player.health, 0)


class BlueBoneTests(unittest.TestCase):
    """A blue bone is only a bone to a heart that is moving."""

    def setUp(self):
        self.player = Entity((0, 0), health=100, attack_damage=10)
        self.wave = Determination(800, 600)
        self.wave.begin(self.player, [Fighter((1, 0), health=30, attack_damage=5)])
        self.wave.shots = [Shot(self.wave.heart, (0, 0), (40, 300), blue=True)]

    def test_holding_still_lets_it_pass_straight_through(self):
        self.wave.moving = False
        self.wave.fly(0.05)
        self.assertEqual(self.player.health, 100)
        self.assertTrue(self.wave.blue_up)  # and the box says so while it is up

    def test_moving_into_it_takes_the_hit(self):
        self.wave.moving = True
        self.wave.fly(0.05)
        self.assertLess(self.player.health, 100)

    def test_a_white_bone_bites_whether_you_move_or_not(self):
        self.wave.shots = [Shot(self.wave.heart, (0, 0), (40, 300))]
        self.wave.moving = False
        self.wave.fly(0.05)
        self.assertLess(self.player.health, 100)
        self.assertFalse(self.wave.blue_up)


if __name__ == "__main__":
    unittest.main()
