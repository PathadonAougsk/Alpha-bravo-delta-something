"""Local stdio MCP server for paused, standalone Pygame battles.

Install requirements-mcp.txt, then let an MCP host launch this file with Python.
No merge entry point is imported and no game results are written to disk.
"""

import os
from pathlib import Path
import sys
import threading
from typing import Any, Literal
import uuid

# Pygame's greeting must never enter the MCP JSON-RPC stdout stream.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
GAME_DIR = Path(__file__).resolve().parent / "Game"
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

try:
    from mcp.server.fastmcp import FastMCP, Image
except ImportError:
    raise SystemExit("Install MCP dependencies: python -m pip install -r requirements-mcp.txt")

from agent import AgentBattle

MAX_SESSIONS = 8
sessions = {}
session_lock = threading.RLock()
mcp = FastMCP(
    "pygame-battle",
    instructions=(
        "Play standalone battles with start_battle, observe_battle, play_turn, "
        "dodge_step, battle_screenshot and quit_battle. Time pauses between calls. "
        "Use available_actions and stable enemy ids from observations. "
        "Spare opens a real dodge wave; gun immediately loses the battle. "
        "This server does not attach to an existing game window or resolve Git files."
    ),
)


def get_session(session_id):
    """Look up an active or completed session, with a useful tool error."""
    if session_id not in sessions:
        raise ValueError("Unknown session_id; call start_battle first.")
    return sessions[session_id]


def observed(session_id, observation):
    return dict(observation, session_id=session_id)


@mcp.tool(structured_output=True)
def start_battle(
    base: float = 50,
    enemy_base: float = 168,
    amount: int = 1,
    seed: int | None = None,
) -> dict[str, Any]:
    """Create a manual, paused battle and return its session_id and observation.

    base/enemy_base: finite stat baselines in [1, 10000]. amount: 0–10 HEADs.
    seed makes combat and dodge patterns reproducible. Up to eight sessions
    can coexist; quit_battle releases a slot. No Git files are read or written.
    """
    with session_lock:
        if len(sessions) >= MAX_SESSIONS:
            raise ValueError("Eight sessions already exist; release one with quit_battle.")
        session = AgentBattle(base, enemy_base, amount, seed)
        session_id = uuid.uuid4().hex
        sessions[session_id] = session
        return observed(session_id, session.observe())


@mcp.tool(structured_output=True)
def observe_battle(session_id: str) -> dict[str, Any]:
    """Read HP, inventory, stable enemy ids, legal actions and visible dodge hazards.

    This does not advance time. result is true for victory, false for defeat,
    and null while unfinished. Rectangles use [x, y, width, height] in pixels;
    coordinates increase rightwards and downwards in an 800×600 field.
    """
    with session_lock:
        return observed(session_id, get_session(session_id).observe())


@mcp.tool(structured_output=True)
def play_turn(
    session_id: str,
    action: Literal["attack", "guard", "health", "gun", "spare", "flee"],
    target: int = 0,
) -> dict[str, Any]:
    """Take one legal action and resolve the enemy round, returning state and events.

    attack uses a living enemy's stable id in target (ignored for other actions).
    guard halves damage and can topple attackers; health spends one healing item.
    gun ends in defeat. spare/flee unlock at half HP: spare starts a dodge wave,
    while flee wastes a turn and enemies attack. Unavailable actions are errors
    and cost no turn. Intro, menu confirmations and cosmetic cutscenes are skipped.
    """
    with session_lock:
        return observed(session_id, get_session(session_id).act(action, target))


@mcp.tool(structured_output=True)
def dodge_step(
    session_id: str,
    direction: Literal[
        "still", "left", "right", "up", "down",
        "up_left", "up_right", "down_left", "down_right",
    ] = "still",
    frames: int = 6,
) -> dict[str, Any]:
    """Hold arrows for 1–48 simulated frames at 48 FPS during DETERMINATION.

    Inspect hazards between short steps. still releases every arrow and avoids
    blue-bone damage. Warning hazards cannot hurt yet. Real collisions reduce
    battle HP; surviving the full wave restores HP and returns the player turn.
    Opening and ending phases also require steps. No time passes between calls.
    """
    with session_lock:
        return observed(session_id, get_session(session_id).dodge_step(direction, frames))


@mcp.tool()
def battle_screenshot(session_id: str) -> Image:
    """Return a PNG of the current agent view without advancing gameplay.

    Uses the game's sprites and actual dodge rendering with a compact agent HUD;
    the keyboard game's command wheel, intro, music and retro filter are omitted.
    """
    with session_lock:
        return Image(data=get_session(session_id).screenshot(), format="png")


@mcp.tool(structured_output=True)
def quit_battle(session_id: str) -> dict[str, Any]:
    """Release a session, abandoning unfinished play with result null.

    Completed sessions retain their result in this final response. Later calls
    with this id fail. No loss streak, merge file or repository is changed.
    """
    with session_lock:
        session = get_session(session_id)
        observation = session.observe() if session.battle.over else session.quit()
        del sessions[session_id]
        return observed(session_id, observation)


@mcp.resource("battle://rules")
def battle_rules() -> str:
    """Read the essential combat rules and tool workflow."""
    return (
        "Start -> observe -> play_turn -> repeat until victory/defeat -> quit. "
        "Use enemy ids, not positions in the living list. Attacks vary ±10%; "
        "2% crits deal triple damage. All living HEADs respond each round. "
        "Guard halves hits with a 40% chance to topple each attacker; toppled "
        "HEADs spend their next round recovering. HEALTH heals 60% of base. "
        "GUN deliberately loses. At <=50% HP spare starts DETERMINATION; "
        "flee spends a turn without escaping. Survive the wave to refill HP. "
        "During a wave call dodge_step with 1–48 frames at 48 FPS. White bones "
        "always hurt, blue bones hurt only while arrows move the heart. Leave "
        "grey warning beams before they fire; move into gaps in white walls. "
        "Battle state and screenshots pause time. Results affect only memory."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
