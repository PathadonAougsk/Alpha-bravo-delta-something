---
name: pygame-battle
description: Play this repository's Feature Branch versus HEAD game through the pygame-battle MCP server, inspecting combat state and choosing turns until the requested outcome.
---

# Play a Pygame battle

Use the connected `pygame-battle` MCP server. Tool names may carry the host's
server prefix. It creates standalone battles using the real game engine and
pauses between calls; it does not control an existing window or resolve Git
conflicts. If tools are missing, use the repository README's MCP setup section
to explain how to connect the server. Never substitute the Git-facing `main.py`:
that entry point has destructive loss tracking.

Call `start_battle` with the user's baselines, enemy count and seed, or its
defaults. Save `session_id` and use it for every later call. If the user supplies
an existing session, call `observe_battle` and continue that session.

Choose from the observation's `available_actions`, then call `play_turn`.
Each call spends one player turn and resolves the entire enemy round. Use
`events` to explain what happened. Enemy `id` values are stable and zero-based;
pass a living enemy's id as `target` for attack, even after earlier enemies die.

- Attack removes enemies' future attacks; finish a hurt HEAD when practical.
- Guard halves incoming hits. An attack that fails against guard topples its
  HEAD, so its next round is spent recovering. Guard itself deals no damage.
- Health heals `heal_amount`, capped at max HP, and spends one item. Account
  for the enemy round that follows it. Inventory includes a separate gun.
- Gun deliberately ends the battle in defeat. Use it when the requested
  objective is to lose, rather than treating it as an offensive weapon.
- Spare and flee unlock at half HP. Flee spends a turn without escaping.
  Spare starts a real dodge wave. Surviving it restores full HP and the turn.

For a dodge wave, inspect `dodge` and call `dodge_step` with short frame batches.
The separate `pygame-determination` skill gives hazard-specific guidance.
Release arrows with `direction="still"` for blue walls. Opening and ending
phases also need steps; regular turns resume only once `state` is `player`.

Use `observe_battle` to inspect without consuming a turn and
`battle_screenshot` when a visual view helps. Both pause gameplay. Do not alter
HP, RNG or source code to obtain a requested result; a seed makes repeatable
play possible through ordinary actions.

Continue until the requested stopping point or `state` becomes `victory` or
`defeat`. `result` is true for a win, false for a loss, and null while unfinished.
Report the outcome and significant turns. Call `quit_battle` when done to free
the session slot; completed results remain in its final response. If the user
wants to resume later, retain the session and include its id. Sessions live only
for the server process lifetime; at most eight coexist.
