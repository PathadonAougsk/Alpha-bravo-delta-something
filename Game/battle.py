"""Turn order for the battle: the player acts, then every living enemy acts."""

import random

from command_menu import ATTACK, GUARD, ITEM, MERCY
from items import GUN, GUN_STOCK, HEALTH, LABELS, ORDER
from stats import BASE, GUARD_FIZZLE, ITEM_HEAL

PLAYER_TURN = "player"
TARGETING = "targeting"      # the cursor is out over the field
CHOOSING_ITEM = "choosing"   # the bag is open
CUTSCENE = "cutscene"        # the gun has come out; the screen is not ours
DODGING = "dodging"          # mercy was offered; the box has the screen instead
RESOLVING = "resolving"
ENEMY_TURN = "enemy"
VICTORY = "victory"
DEFEAT = "defeat"

# the states that sit and wait on the player, or on something being watched,
# rather than on the clock
WAITING = (PLAYER_TURN, TARGETING, CHOOSING_ITEM, CUTSCENE, DODGING)

STARTING_ITEMS = 3
BEAT = 0.8  # seconds a result message stays up before the next actor moves


class Battle:
    def __init__(self, player, enemies, items=STARTING_ITEMS, base=BASE, fizzle=GUARD_FIZZLE):
        self.player = player
        self.enemies = enemies
        self.stock = {HEALTH: items, GUN: GUN_STOCK}
        self.fizzle = fizzle
        self.item_heal = max(1, round(base * ITEM_HEAL))
        self.state = PLAYER_TURN
        self.message = "Arrows pick a command, Enter confirms."
        self.timer = 0.0
        self._queue = []
        self._target = None  # the HEAD the cursor is sitting on
        self._item = 0       # which row of the bag is picked
        if not self.living_enemies:
            self.state = VICTORY
            self.message = "Nothing to fight."

    # ------------------------------------------------------------------ state

    @property
    def over(self):
        return self.state in (VICTORY, DEFEAT)

    @property
    def result(self):
        """True when the player won, False when they lost, None mid-fight."""
        if self.state == VICTORY:
            return True
        if self.state == DEFEAT:
            return False
        return None

    @property
    def accepting_input(self):
        return self.state == PLAYER_TURN

    @property
    def choosing_target(self):
        """True while the cursor is out and waiting for a HEAD to be picked."""
        return self.state == TARGETING

    @property
    def choosing_item(self):
        """True while the bag is open and waiting for a row to be picked."""
        return self.state == CHOOSING_ITEM

    @property
    def watching_cutscene(self):
        """True while the gun's cut-in owns the screen."""
        return self.state == CUTSCENE

    @property
    def dodging(self):
        """True while the mercy box owns the screen."""
        return self.state == DODGING

    @property
    def items(self):
        """Everything left in the bag, gun and all - what the HUD counts."""
        return sum(self.stock.values())

    @property
    def item_index(self):
        """Which row of the bag the pick is on - what the panel draws lit."""
        return self._item

    @property
    def item(self):
        """The row of the bag the pick is on."""
        return ORDER[self._item]

    @property
    def living_enemies(self):
        return [e for e in self.enemies if e.alive]

    @property
    def target(self):
        """The enemy the cursor is on - the one an ATTACK would hit."""
        living = self.living_enemies
        if not living:
            return None
        return self._target if self._target in living else living[0]

    # ----------------------------------------------------------------- actions

    def player_command(self, action):
        """Run the chosen command. Anything that costs a turn hands over to the enemies."""
        if not self.accepting_input:
            return

        if action == ATTACK:
            if self.target is None:
                return
            # picking ATTACK does not cost the turn: it hands the arrows over
            # to the cursor, and the swing waits on a target
            self._target = self.target
            self.state = TARGETING
            self.message = "Pick a HEAD - arrows move, Enter strikes."
            return

        elif action == GUARD:
            self.player.guard()
            self.message = "Guarding - damage halved, and blows can glance off."

        elif action == MERCY:
            # mercy is not a turn so much as a dare: the HEADs answer it all at
            # once, and the box holds the screen until the wave is out
            self.state = DODGING
            self.message = f"{self.player.name} offers mercy. The HEADs answer."
            return

        elif action == ITEM:
            if self.items <= 0:
                self.message = "Out of items."
                return  # a wasted press does not cost the turn
            # like ATTACK, opening the bag is free: what is taken out costs
            self.state = CHOOSING_ITEM
            self.message = "Open the bag - arrows move, Enter uses."
            return

        else:
            return

        self._begin(RESOLVING)

    def move_target(self, step):
        """Walk the cursor `step` places along the living HEADs, wrapping round."""
        living = self.living_enemies
        if not self.choosing_target or len(living) < 2:
            return
        here = living.index(self.target)
        self._target = living[(here + step) % len(living)]

    def cancel_target(self):
        """Put the cursor away; the turn has not been spent."""
        if not self.choosing_target:
            return
        self.state = PLAYER_TURN
        self.message = "Arrows pick a command, Enter confirms."

    def confirm_target(self):
        """Swing at whoever the cursor is on. This is what costs the turn."""
        if not self.choosing_target:
            return
        target = self.target
        if target is None:
            return
        self.player.attack(target)
        self.message = (
            f"{self.player.name} hits {target.name} "
            f"for {self.player.attack_damage}!"
        )
        if not target.alive:
            self.message += f" {target.name} is down."
        self._begin(RESOLVING)

    # ------------------------------------------------------------------- bag

    def move_item(self, step):
        """Walk the pick `step` rows down the bag, wrapping round."""
        if not self.choosing_item:
            return
        self._item = (self._item + step) % len(ORDER)

    def cancel_item(self):
        """Shut the bag; the turn has not been spent."""
        if not self.choosing_item:
            return
        self.state = PLAYER_TURN
        self.message = "Arrows pick a command, Enter confirms."

    def confirm_item(self):
        """Use whatever the pick is on. An empty row does not cost the turn."""
        if not self.choosing_item:
            return
        name = self.item
        if self.stock[name] <= 0:
            self.message = f"No {LABELS[name]} left."
            return
        self.stock[name] -= 1

        if name == GUN:
            # nothing else happens this turn, or any turn after it
            self.state = CUTSCENE
            self.message = f"{self.player.name} raises the gun."
            return

        self.player.heal(self.item_heal)
        self.message = f"Used HEALTH - healed {self.item_heal} HP."
        self._begin(RESOLVING)

    def finish_cutscene(self):
        """The shot has gone off. There is no round after it."""
        if not self.watching_cutscene:
            return
        self.player.health = 0
        self.state = DEFEAT
        self.message = f"{self.player.name} is gone - DEFEAT."

    def finish_dodge(self, survived, taken=0):
        """The wave is out. Living through it buys the turn straight back.

        The wave was the HEADs' round: one that the guard put on its back
        spent it getting up, and the guard itself is spent along with it.
        """
        if not self.dodging:
            return
        if not survived or not self.player.alive:
            self.player.health = 0
            self.state = DEFEAT
            self.message = f"{self.player.name}'s heart breaks - DEFEAT."
            return
        for enemy in self.living_enemies:
            if enemy.recovering:
                enemy.recover()
        self.player.guarding = False
        self.state = PLAYER_TURN
        self.message = (
            "Not a scratch - your move."
            if not taken
            else f"Through it, {taken} HP down - your move."
        )

    def update(self, dt):
        """Drive the non-interactive parts of the turn on a timer."""
        if self.over or self.state in WAITING:
            return

        self.timer -= dt
        if self.timer > 0:
            return

        if self.state == RESOLVING:
            if not self.living_enemies:
                self.state = VICTORY
                self.message = "Every HEAD is down - VICTORY!"
                return
            self._queue = list(self.living_enemies)
            self._begin(ENEMY_TURN)

        elif self.state == ENEMY_TURN:
            self._enemy_step()

    def _enemy_step(self):
        while self._queue:
            enemy = self._queue.pop(0)
            if not enemy.alive:
                continue

            if enemy.recovering:
                # knocked off its feet last round: this turn goes on standing up
                enemy.recover()
                self.message = f"{enemy.name} picks itself back up."
                self._begin(ENEMY_TURN)
                return

            if self.player.guarding and random.random() < self.fizzle:
                # the guard turned the swing aside and took the attacker with it
                enemy.lunge_at(self.player)
                enemy.fail_attack()
                self.message = (
                    f"{enemy.name}'s attack fails against "
                    f"{self.player.name}'s guard!"
                )
                self._begin(ENEMY_TURN)
                return

            before = self.player.health
            enemy.attack(self.player)
            dealt = before - self.player.health
            self.message = f"{enemy.name} hits {self.player.name} for {dealt}!"
            if not self.player.alive:
                self.state = DEFEAT
                self.message = f"{enemy.name} finishes {self.player.name} off - DEFEAT."
                return
            self._begin(ENEMY_TURN)
            return

        # every enemy has acted; the guard only covered that round
        self.player.guarding = False
        self.state = PLAYER_TURN
        self.message = "Your move."

    def _begin(self, state):
        self.state = state
        self.timer = BEAT
