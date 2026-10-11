---
name: pygame-battle
description: Play Feature Branch versus HEAD through the standalone pygame-battle MCP server, or manually play the configured Pygame Git mergetool when the user requests conflict resolution through the game.
---

# Play a Pygame battle

## Choose the requested mode

For Git conflict resolution through the game, use the configured `git
mergetool` and its actual windows. Read [the WSL instructions](../../AGENTS.md)
for local display access, loss tracking, manual controls, and verification.
The [WSL menu helper](scripts/wsl_mergetool_ui.py) sends explicitly selected
keystrokes and captures the live game; it does not choose turns or enable
autobattle. Do not use standalone MCP battle results to resolve Git files.
The Git-facing game can delete `.git` after three consecutive losses.
Follow the project's `AGENTS.md` and the user's instructions for accepting
losses; this project's workflow disallows protective backups and accepts
the game's consequences without resetting its loss counter.

For standalone battles, use the connected `pygame-battle` MCP server.
Tool names may carry the host's
server prefix. It creates standalone battles using the real game engine and
pauses between calls; it does not control an existing window or resolve Git
conflicts. If tools are missing, use the repository README's MCP setup section
to explain how to connect the server. Do not substitute the Git-facing
`main.py` for a standalone battle: it has destructive loss tracking.

## Standalone MCP play

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
