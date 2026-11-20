import json
import os
import subprocess
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if "NT_DATAROOT" not in os.environ:
    os.environ["NT_DATAROOT"] = os.path.join(PROJECT_ROOT, "spellbook/")

from unittest.mock import patch

from witchcraft.interface.mcp.mcp_server import WitchcraftMCPServer
from witchcraft.interface.ai.harpia_agent import (
    harpia_chat,
    harpia_resume_approval,
    _extract_inline_tool_calls,
)


class TestWitchcraftMCP(unittest.TestCase):

    def setUp(self):
        self.mcp = WitchcraftMCPServer()

    def test_initialize(self):
        resp = self.mcp.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            }
        )
        self.assertEqual(resp["id"], 1)
        self.assertIn("capabilities", resp["result"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "witchcraft-fex-mcp")

    def test_tools_list_contains_binds_and_cmd_backend(self):
        resp = self.mcp.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        tools = resp["result"]["tools"]
        self.assertGreater(len(tools), 200)
        names = {t["name"] for t in tools}
        self.assertIn("witchcraft_system_stats", names)
        self.assertIn("witchcraft_search_binds", names)
        self.assertIn("witchcraft_xcript_eval", names)
        self.assertIn("nmap_syn_scan", names)

    def test_search_binds_by_cmd_backend(self):
        resp = self.mcp.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "witchcraft_search_binds",
                    "arguments": {"cmd_backend": "nmap"},
                },
            }
        )
        self.assertFalse(resp["result"]["isError"])
        data = json.loads(resp["result"]["content"][0]["text"])
        self.assertGreaterEqual(data["total"], 2)
        for item in data["results"]:
            self.assertEqual(item["cmd_backend"], "nmap")

    def test_xcript_eval_tool(self):
        resp = self.mcp.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "witchcraft_xcript_eval",
                    "arguments": {
                        "code": 'declare msg = "mcp_xcript_ok"; echo msg'
                    },
                },
            }
        )
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], 0)
        self.assertEqual(payload["stdout"], "mcp_xcript_ok")

    def test_resources_and_prompts(self):
        res_list = self.mcp.handle_request(
            {"jsonrpc": "2.0", "id": 5, "method": "resources/list"}
        )
        uris = [r["uri"] for r in res_list["result"]["resources"]]
        self.assertIn("witchcraft://database/rocketdb", uris)

        res_read = self.mcp.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "resources/read",
                "params": {"uri": "witchcraft://database/rocketdb"},
            }
        )
        db_content = json.loads(res_read["result"]["contents"][0]["text"])
        self.assertIn("index", db_content)
        self.assertIn("cmd_backend", db_content["index"][0])

        prompt_get = self.mcp.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "prompts/get",
                "params": {
                    "name": "opsec_recon",
                    "arguments": {"target": "example.com"},
                },
            }
        )
        self.assertIn("example.com", prompt_get["result"]["description"])

    def test_stdio_end_to_end(self):
        main_py = os.path.join(PROJECT_ROOT, "main.py")
        req = json.dumps(
            {"jsonrpc": "2.0", "id": 99, "method": "ping"}
        ) + "\n"
        proc = subprocess.run(
            [sys.executable, main_py, "server.mcp"],
            input=req,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=PROJECT_ROOT,
        )
        self.assertEqual(proc.returncode, 0)
        resp = json.loads(proc.stdout.strip())
        self.assertEqual(resp["id"], 99)
        self.assertEqual(resp["result"], {})

    def test_harpia_chat_xcript_shortcut(self):
        res = harpia_chat('/xcript declare msg = "harpia_ok"; echo msg')
        self.assertEqual(res["status"], "ok")
        self.assertIn("harpia_ok", res["reply"])
        self.assertEqual(len(res["tool_calls"]), 1)
        self.assertEqual(res["tool_calls"][0]["name"], "witchcraft_xcript_eval")

    def test_shell_exec_mcp_tool(self):
        resp = self.mcp.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 20,
                "method": "tools/call",
                "params": {
                    "name": "witchcraft_shell_exec",
                    "arguments": {
                        "command": "printf 'alpha\\nbeta\\n' | grep beta",
                        "reason": "filter lines with pipe",
                    },
                },
            }
        )
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], 0)
        self.assertEqual(payload["stdout"].strip(), "beta")

    def test_extract_multiple_inline_tool_calls(self):
        text = (
            '<tool_call>{"name": "witchcraft_search_binds", "arguments": {"query": "dns"}}</tool_call>\n'
            '<tool_call>{"name": "witchcraft_shell_exec", "arguments": {"command": "echo hi", "reason": "test"}}</tool_call>'
        )
        calls = _extract_inline_tool_calls(text)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["name"], "witchcraft_search_binds")
        self.assertEqual(calls[1]["name"], "witchcraft_shell_exec")

    def test_agentic_loop_chaining_and_untruncated_output(self):
        long_marker = "Z" * 4500
        seen_llm_messages = []
        printed_records = []

        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "content": '<tool_call>{"name": "witchcraft_search_binds", "arguments": {"cmd_backend": "nmap"}}</tool_call>'
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '<tool_call>{"name": "witchcraft_shell_exec", '
                                f'"arguments": {{"command": "python3 -c \\"print(\'HEAD_\' + \'Z\'*4500 + \'_TAIL\')\\"", "reason": "long output"}}}}</tool_call>'
                            )
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "Chaining complete: found nmap binds and ran shell command."
                        }
                    }
                ]
            },
        ]

        def fake_llm(messages, tools=None, llm_url=None):
            seen_llm_messages.append([dict(m) for m in messages])
            return responses.pop(0)

        with patch("witchcraft.interface.ai.harpia_agent._call_llama_completion", side_effect=fake_llm):
            res = harpia_chat(
                "find nmap binds then run a shell test",
                shell_mode="auto",
                max_steps=5,
                on_tool_output=lambda rec: printed_records.append(rec),
            )

        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(res["tool_calls"]), 2)
        self.assertEqual(len(printed_records), 2)
        self.assertIn(long_marker, res["tool_calls"][1]["output"])
        self.assertIn(long_marker, printed_records[1]["output"])

        last_llm_obs = seen_llm_messages[-1][-1]["content"]
        self.assertIn("truncated for LLM summary context", last_llm_obs)
        self.assertNotIn(long_marker, last_llm_obs)

    def test_shell_propose_approval_pause_and_resume(self):
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "content": '<tool_call>{"name": "witchcraft_shell_exec", "arguments": {"command": "echo proposed_ok", "reason": "verify shell"}}</tool_call>'
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": "Command executed and returned proposed_ok."
                        }
                    }
                ]
            },
        ]

        def fake_llm(messages, tools=None, llm_url=None):
            return responses.pop(0)

        with patch("witchcraft.interface.ai.harpia_agent._call_llama_completion", side_effect=fake_llm):
            paused = harpia_chat("run echo", shell_mode="propose")
            self.assertEqual(paused["status"], "awaiting_approval")
            self.assertEqual(paused["pending_action"]["command"], "echo proposed_ok")

            resumed = harpia_resume_approval(paused["session_id"], approved=True)
            self.assertEqual(resumed["status"], "ok")
            self.assertEqual(len(resumed["tool_calls"]), 1)
            self.assertIn("proposed_ok", resumed["tool_calls"][0]["output"])
            self.assertIn("proposed_ok", resumed["reply"])


if __name__ == "__main__":
    unittest.main()

