---
name: pygame-determination
description: Steer the DETERMINATION heart and dodge bones, walls, pellets and skull beams in an active pygame-battle MCP session.
---

# Survive DETERMINATION

Use `observe_battle` with the user's active `session_id`. This skill applies to
the `pygame-battle` MCP server's dodge wave. If `state` is `player`, `spare` in
`available_actions` starts one through `play_turn`. Do not restart a supplied
session or open a wave unless that serves the user's requested play.

`dodge_step` holds a direction for `frames` simulated frames at 48 FPS, then
returns a new observation. Time stops between calls, so inspect hazards before
choosing the next movement. Start with 3–6 frames near danger; up to 48 frames
is useful during opening or ending phases. `still` releases every arrow.
Directions include the four cardinal directions and `up_left`, `up_right`,
`down_left`, `down_right`. Diagonal movement is normalized.

The field is 800×600. Coordinates increase rightwards and downwards.
`box` and hazard `rect` are `[x, y, width, height]`; `heart` is `[x, y]`.
The collision square extends `hitbox_half_size` pixels either side of the heart.
Movement speed is `speed` pixels per second, about 5.94 pixels per frame. For a
moving bone, project its rectangle using `velocity * frames / 48`; include the
heart's own displacement and allow room for both hitboxes.

- White bones and walls hurt even when standing still. Look for the open lane
  in rain and sweeps, or the gap between the two segments of a white wall.
- Blue bones hurt only while movement arrows are held. When
  `blue_wall_present` is true, use `still` while the wall crosses. Holding an
  arrow into the edge still counts as movement.
- Pellets aim at the heart's position when they appear. Move away during
  `warning_seconds`, then avoid their projected path.
- Blasters warn along their eventual beam rectangle. Move perpendicular to
  `axis` before `warning_seconds` reaches zero. `live=false` means a warning
  cannot currently hurt; it does not mean that location will remain safe.
- `invulnerable_seconds` is the grace period after a hit. The wave still uses
  the battle's actual HP and `damage_per_hit`; it can end in defeat.

Call `battle_screenshot` if the geometry is unclear. Rendering and observation
do not advance time. In `opening`, the heart cannot move yet; step until
`dodge.phase` is `dodging`. In `leaving` or `breaking`, continue stepping to
finish the transition. Surviving restores full HP and returns `state="player"`;
dying returns `state="defeat"`. Do not assume survival before the engine reports
it. Continue normal battle play or return control at the user's stopping point.
