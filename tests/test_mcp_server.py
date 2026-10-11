"""Real stdio MCP integration; requires requirements-mcp.txt."""

import asyncio
import base64
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("mcp"), "Install requirements-mcp.txt for MCP integration")
class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_tools_resources_gameplay_and_cleanup(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def exercise():
            with tempfile.TemporaryDirectory() as directory:
                sandbox = Path(directory)
                git_file = sandbox / ".git" / "keep"
                git_file.parent.mkdir()
                git_file.write_bytes(b"repository fixture")
                merge_file = sandbox / "MERGED"
                merge_file.write_bytes(b"<<<<<<< HEAD\nhead\n=======\nfeature\n>>>>>>> branch\n")
                parameters = StdioServerParameters(
                    command=sys.executable,
                    args=[str(ROOT / "mcp_game_server.py")],
                    cwd=directory,
                )
                async with stdio_client(parameters) as (read, write):
                    async with ClientSession(read, write) as client:
                        await client.initialize()
                        listed = await client.list_tools()
                        self.assertEqual({tool.name for tool in listed.tools}, {
                            "start_battle", "observe_battle", "play_turn", "dodge_step",
                            "battle_screenshot", "quit_battle",
                        })
                        rules = await client.read_resource("battle://rules")
                        self.assertIn("GUN deliberately loses", rules.contents[0].text)

                        async def call(name, **arguments):
                            result = await client.call_tool(name, arguments)
                            self.assertFalse(result.isError, result.content)
                            data = result.structuredContent
                            # Text results remain usable by older MCP clients.
                            text_data = json.loads(result.content[0].text)
                            self.assertEqual(data, text_data)
                            return data

                        started = await call("start_battle", enemy_base=1, amount=2, seed=7)
                        session_id = started["session_id"]
                        self.assertEqual(await call("observe_battle", session_id=session_id), started)
                        rejected = await client.call_tool("play_turn", {
                            "session_id": session_id, "action": "attack", "target": -1,
                        })
                        self.assertTrue(rejected.isError)
                        self.assertEqual(await call("observe_battle", session_id=session_id), started)
                        await call("play_turn", session_id=session_id, action="attack", target=0)
                        won = await call("play_turn", session_id=session_id, action="attack", target=1)
                        self.assertIs(won["result"], True)
                        png = await client.call_tool("battle_screenshot", {"session_id": session_id})
                        self.assertFalse(png.isError)
                        self.assertEqual(png.content[0].type, "image")
                        self.assertTrue(base64.b64decode(png.content[0].data).startswith(b"\x89PNG"))
                        released = await call("quit_battle", session_id=session_id)
                        self.assertIs(released["result"], True)
                        missing = await client.call_tool("observe_battle", {"session_id": session_id})
                        self.assertTrue(missing.isError)

                        started = await call("start_battle", seed=1)
                        session_id = started["session_id"]
                        state = started
                        for _ in range(6):
                            if "spare" in state["available_actions"]:
                                break
                            state = await call("play_turn", session_id=session_id, action="attack")
                        self.assertIn("spare", state["available_actions"])
                        state = await call("play_turn", session_id=session_id, action="spare")
                        self.assertEqual(state["state"], "dodging")
                        state = await call("dodge_step", session_id=session_id, direction="right", frames=24)
                        self.assertEqual(state["dodge"]["phase"], "dodging")
                        await call("quit_battle", session_id=session_id)

                        # Losses here must never call the Git loss-tracking path.
                        for _ in range(3):
                            started = await call("start_battle", seed=1)
                            lost_id = started["session_id"]
                            lost = await call("play_turn", session_id=lost_id, action="gun")
                            self.assertIs(lost["result"], False)
                            await call("quit_battle", session_id=lost_id)
                        self.assertEqual(git_file.read_bytes(), b"repository fixture")
                        self.assertEqual(merge_file.read_bytes(), b"<<<<<<< HEAD\nhead\n=======\nfeature\n>>>>>>> branch\n")
                        self.assertFalse((sandbox / ".feature_branch_loss_streak").exists())
        await asyncio.wait_for(exercise(), timeout=30)


if __name__ == "__main__":
    unittest.main()
