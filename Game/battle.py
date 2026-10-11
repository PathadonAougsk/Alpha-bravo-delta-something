"""Turn order for the battle: the player acts, then every living enemy acts."""

import random

from command_menu import ATTACK, GUARD, ITEM, DETERMINATION
from items import GUN, GUN_STOCK, HEALTH, LABELS, ORDER
from stats import BASE, GUARD_FIZZLE, ITEM_HEAL, DETERMINATION_AT

PLAYER_TURN = "player"
TARGETING = "targeting"      # the cursor is out over the field
CHOOSING_ITEM = "choosing"   # the bag is open
CHOOSING_DETERMINATION = "determination"  # the box is open, asking what
                                          # determination turns out to mean
CUTSCENE = "cutscene"        # the gun has come out; the screen is not ours
DODGING = "dodging"          # you stood your ground; the box has the screen
RESOLVING = "resolving"
ENEMY_TURN = "enemy"
VICTORY = "victory"
DEFEAT = "defeat"

# the states that sit and wait on the player, or on something being watched,
# rather than on the clock
WAITING = (
    PLAYER_TURN, TARGETING, CHOOSING_ITEM, CHOOSING_DETERMINATION, CUTSCENE,
    DODGING,
)

STARTING_ITEMS = 3
BEAT = 0.8  # seconds a result message stays up before the next actor moves
ALWAYS_AUTOBATTLE = False  # set to True to enable autobattle for every battle

# What DETERMINATION turns out to mean, once you have picked it. Standing
# there and sparing them is the dare the box was built for; running is the
# other thing you could do with a turn, and it is worth finding out what it
# costs.
SPARE = "spare"
FLEE = "flee"
DETERMINATION_ORDER = (SPARE, FLEE)
DETERMINATION_LABELS = {SPARE: "Spare", FLEE: "Flee"}

# What the box says while it is asking. You are the one digging in, so you
# are the one talking, and it is your face in the margin. It is not an offer
# any more - nothing here is being held out to the HEADs - it is you deciding
# out loud that you are still in the file when this is over.
DETERMINATION_LINES = (
    "* You set your feet and stop giving ground.",
    '* "Not this hunk. Not this file. Not today."',
)
DETERMINATION_LOW = 0.25  # at or under this share of your health the box
                          # stops saying what you do and starts saying what
                          # you tell yourself
DETERMINATION_LINES_LOW = (
    "* Please don't give up.",
    "* Stay Determined!",
)


class Battle:
    def __init__(
        self,
        player,
        enemies,
        items=STARTING_ITEMS,
        base=BASE,
        fizzle=GUARD_FIZZLE,
        determination_at=DETERMINATION_AT,
        autobattle=None,
    ):
        self.player = player
        self.enemies = enemies
        self.stock = {HEALTH: items, GUN: GUN_STOCK}
        self.fizzle = fizzle
        self.determination_at = determination_at
        self.item_heal = max(1, round(base * ITEM_HEAL))
        self.state = PLAYER_TURN
        self.message = "Arrows + Enter: command. A: autobattle."
        self.autobattle_enabled = False
        self._first_turn = True
        self.timer = 0.0
        self._queue = []
        self._target = None  # the HEAD the cursor is sitting on
        self._item = 0       # which row of the bag is picked
        self.items_used = 0  # counted up so the screen can flash on each use
        self._determination = 0      # and which way out of the box is picked
        if not self.living_enemies:
            self.state = VICTORY
            self.message = "Nothing to fight."
        elif (ALWAYS_AUTOBATTLE if autobattle is None else autobattle):
            self.autobattle_enabled = True
            self.message = "Autobattle active."

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
        return self.state == PLAYER_TURN and not self.autobattle_enabled

    @property
    def can_autobattle(self):
        """Whether autobattle can still be started on the opening turn."""
        return self.accepting_input and self._first_turn

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
    def determination_ready(self):
        """True once you are hurt enough to be allowed to offer determination.

        Determination is what you reach for when the fight is already going badly, so
        the box will not open while you are still standing comfortably.
        """
        return self.player.health <= self.player.max_health * self.determination_at

    @property
    def locked(self):
        """The commands the wheel should draw greyed out, as things stand."""
        return () if self.determination_ready else (DETERMINATION,)

    @property
    def choosing_determination(self):
        """True while the determination box is open and waiting on Spare or Flee."""
        return self.state == CHOOSING_DETERMINATION

    @property
    def dodging(self):
        """True while the determination box owns the screen."""
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

    def autobattle(self):
        """Start automatic attacks on the first turn; return whether started."""
        if not self.can_autobattle:
            return False
        self.autobattle_enabled = True
        self._auto_attack()
        return True

    def player_command(self, action):
        """Run the chosen command. Anything that costs a turn hands over to the enemies."""
        if not self.accepting_input:
            return
        self._run_player_command(action)

    def _run_player_command(self, action):
        if action == ATTACK:
            if self.target is None:
                return
            # picking ATTACK does not cost the turn: it hands the arrows over
            # to the cursor, and the swing waits on a target
            self._target = self.target
            self.state = TARGETING
            self.message = "Pick a HEAD - arrows move, Enter strikes, X backs out."
            return

        elif action == GUARD:
            self.player.guard()
            self.message = "Guarding - damage halved, and blows can glance off."

        elif action == DETERMINATION:
            if not self.determination_ready:
                self.message = (
                    f"DETERMINATION opens at "
                    f"{round(self.determination_at * 100)}% HP - "
                    "you are not hurt enough yet."
                )
                return  # a wasted press does not cost the turn
            # picking DETERMINATION does not cost the turn either: it opens the box,
            # and what determination turns out to mean is a second question
            self._determination = 0
            self.state = CHOOSING_DETERMINATION
            self.message = (
                "Spare them, or run - arrows pick, Enter confirms, X backs out."
            )
            return

        elif action == ITEM:
            if self.items <= 0:
                self.message = "Out of items."
                return  # a wasted press does not cost the turn
            # like ATTACK, opening the bag is free: what is taken out costs
            self.state = CHOOSING_ITEM
            self.message = "Open the bag - arrows move, Enter uses, X backs out."
            return

        else:
            return

        self._first_turn = False
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
        before = target.health
        self.player.attack(target)
        dealt = before - target.health
        self.message = (
            f"{self.player.name} hits {target.name} "
            f"for {dealt}!"
        )
        if self.player.last_attack_critical:
            self.message += " Critical hit!"
        if not target.alive:
            self.message += f" {target.name} is down."
        self._first_turn = False
        self._begin(RESOLVING)

    def _auto_attack(self):
        """Autobattle's whole turn: put the cursor on a HEAD and swing at it."""
        self._run_player_command(ATTACK)
        self.confirm_target()

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
        self.items_used += 1
        self._first_turn = False

        if name == GUN:
            # nothing else happens this turn, or any turn after it
            self.state = CUTSCENE
            self.message = f"{self.player.name} raises the gun."
            return

        self.player.heal(self.item_heal)
        self.message = f"Used HEALTH - healed {self.item_heal} HP."
        self._begin(RESOLVING)

    # ----------------------------------------------------------------- determination

    @property
    def determination_index(self):
        """Which way out of the box is picked - what the soul sits in front of."""
        return self._determination

    @property
    def determination_option(self):
        return DETERMINATION_ORDER[self._determination]

    @property
    def determination_labels(self):
        """The choices as the box spells them out, in the order it lays them."""
        return [DETERMINATION_LABELS[name] for name in DETERMINATION_ORDER]

    @property
    def determination_lines(self):
        """What the box has to say while it asks - which depends on the state you are in."""
        if self.player.health <= self.player.max_health * DETERMINATION_LOW:
            return DETERMINATION_LINES_LOW
        return DETERMINATION_LINES

    def move_determination(self, step):
        """Walk the pick `step` places along the choices, wrapping round."""
        if not self.choosing_determination:
            return
        self._determination = (self._determination + step) % len(DETERMINATION_ORDER)

    def cancel_determination(self):
        """Shut the box; the turn has not been spent."""
        if not self.choosing_determination:
            return
        self.state = PLAYER_TURN
        self.message = "Arrows pick a command, Enter confirms."

    def confirm_determination(self):
        """Take the pick. Either way the turn is spent on it."""
        if not self.choosing_determination:
            return
        self._first_turn = False

        if self.determination_option == FLEE:
            # there is no running from a formation that has already surrounded
            # you: the turn goes on finding that out, and they get their round
            self.message = f"{self.player.name} runs - the HEADs close the gap."
            self._begin(RESOLVING)
            return

        # determination is not a turn so much as a dare: the HEADs answer it all at
        # once, and the box holds the screen until the wave is out
        self.state = DODGING
        self.message = f"{self.player.name} stands their ground. The HEADs answer."

    def finish_cutscene(self):
        """The shot has gone off. There is no round after it."""
        if not self.watching_cutscene:
            return
        self.player.health = 0
        self.state = DEFEAT
        self.message = f"{self.player.name} is gone - DEFEAT."

    def finish_dodge(self, survived, taken=0):
        """The wave is out. Living through it buys the turn straight back.

        It buys back the HP too, all of it: the wave is the hardest thing in
        the fight and it is offered at half health or less, so what you get
        for not being hit for a whole round is a whole bar. That is also what
        makes it worth the risk of walking into one on purpose.

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
        back = self.player.max_health - self.player.health
        self.player.heal(self.player.max_health)
        self.state = PLAYER_TURN
        if not back:
            self.message = "Not a scratch - your move."
        elif taken:
            self.message = f"Through it, {taken} HP down - and all {back} back."
        else:
            self.message = f"Not a scratch - and all {back} HP back."

    def update(self, dt):
        """Drive the non-interactive parts of the turn on a timer."""
        if self.over:
            return
        if self.state == PLAYER_TURN and self.autobattle_enabled:
            self._auto_attack()
            return
        if self.state in WAITING:
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
            if enemy.last_attack_critical:
                self.message += " Critical hit!"
            if not self.player.alive:
                self.state = DEFEAT
                self.message += f" {self.player.name} is down - DEFEAT."
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
