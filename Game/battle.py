"""Turn order for the battle: the player acts, then every living enemy acts."""

from command_menu import ATTACK, GUARD, ITEM
from stats import BASE, ITEM_HEAL

PLAYER_TURN = "player"
RESOLVING = "resolving"
ENEMY_TURN = "enemy"
VICTORY = "victory"
DEFEAT = "defeat"

STARTING_ITEMS = 3
BEAT = 0.8  # seconds a result message stays up before the next actor moves


class Battle:
    def __init__(self, player, enemies, items=STARTING_ITEMS, base=BASE):
        self.player = player
        self.enemies = enemies
        self.items = items
        self.item_heal = max(1, round(base * ITEM_HEAL))
        self.state = PLAYER_TURN
        self.message = "Arrows + Enter: command. A: autobattle."
        self.autobattle_enabled = False
        self._first_turn = True
        self.timer = 0.0
        self._queue = []
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
        return self.state == PLAYER_TURN and not self.autobattle_enabled

    @property
    def can_autobattle(self):
        """Whether autobattle can still be started on the opening turn."""
        return self.accepting_input and self._first_turn

    @property
    def living_enemies(self):
        return [e for e in self.enemies if e.alive]

    @property
    def target(self):
        """The enemy an ATTACK would hit."""
        living = self.living_enemies
        return living[0] if living else None

    # ----------------------------------------------------------------- actions

    def autobattle(self):
        """Start automatic attacks on the first turn; return whether started."""
        if not self.can_autobattle:
            return False
        self.autobattle_enabled = True
        self._run_player_command(ATTACK)
        return True

    def player_command(self, action):
        """Run the chosen command. Anything that costs a turn hands over to the enemies."""
        if not self.accepting_input:
            return
        self._run_player_command(action)

    def _run_player_command(self, action):
        if action == ATTACK:
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

        elif action == GUARD:
            self.player.guard()
            self.message = "Guarding - incoming damage halved."

        elif action == ITEM:
            if self.items <= 0:
                self.message = "Out of items."
                return  # a wasted press does not cost the turn
            self.items -= 1
            self.player.heal(self.item_heal)
            self.message = f"Used an item - healed {self.item_heal} HP."

        else:
            return

        self._first_turn = False
        self._begin(RESOLVING)

    def update(self, dt):
        """Drive the non-interactive parts of the turn on a timer."""
        if self.over:
            return
        if self.state == PLAYER_TURN:
            if self.autobattle_enabled:
                self._run_player_command(ATTACK)
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
