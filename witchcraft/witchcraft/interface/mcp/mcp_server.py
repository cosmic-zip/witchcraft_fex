import io
import json
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr

from witchcraft.metalcore.core import *
from witchcraft.modules.system.nt_stats import get_system_metrics


MCP_PROTOCOL_VERSION = "2024-11-05"


def _sanitize_tool_name(name: str) -> str:
    """Convert bind names like 'mac.spoof' into MCP-safe 'mac_spoof'."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return cleaned[:64]


class WitchcraftMCPServer:
    """
    Model Context Protocol (MCP) JSON-RPC 2.0 server for WitchcraftFEX.
    Exposes rocketdb_v2.json binds, native modules, Xcript runtime, and resources over stdio.
    """

    def __init__(self):
        self.db = read_db() or []
        self._tool_map = {}
        self._build_tool_index()

    def _build_tool_index(self):
        self._tool_map.clear()
        for bind in self.db:
            raw_name = bind.get("name", "")
            if not raw_name:
                continue
            mcp_name = _sanitize_tool_name(raw_name)
            self._tool_map[mcp_name] = bind
            self._tool_map[raw_name] = bind

    def get_tools(self) -> list:
        tools = [
            {
                "name": "witchcraft_system_stats",
                "description": "Collect real-time system telemetry (OS, CPU, memory, GPU, containers, VMs, processes, network).",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "witchcraft_search_binds",
                "description": "Search WitchcraftFEX rocketdb binds by keyword, category, or cmd_backend.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Keyword to match against bind name or description.",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category (e.g., network, security, system, web, forensics, firewall, database).",
                        },
                        "cmd_backend": {
                            "type": "string",
                            "description": "Filter by underlying command backend (e.g., nmap, curl, hashcat, iptables, witchcraft).",
                        },
                    },
                },
            },
            {
                "name": "witchcraft_xcript_eval",
                "description": "Execute a Witchcraft-Xcript (.xcript) inline script or script file using the static Xcript binary.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Inline Xcript source code to evaluate.",
                        },
                        "file": {
                            "type": "string",
                            "description": "Path to a .xcript file to execute.",
                        },
                    },
                },
            },
        ]

        seen = {t["name"] for t in tools}
        for bind in self.db:
            raw_name = bind.get("name", "")
            if not raw_name:
                continue
            mcp_name = _sanitize_tool_name(raw_name)
            if mcp_name in seen:
                continue
            seen.add(mcp_name)

            category = bind.get("category", "general")
            backend = bind.get("cmd_backend", "shell")
            desc = bind.get("description", "WitchcraftFEX bind")
            full_desc = f"[{category} | backend: {backend}] ({raw_name}) {desc}"

            properties = {}
            required = []
            arguments = bind.get("arguments") or {}
            if isinstance(arguments, dict):
                for arg_name, arg_meta in arguments.items():
                    arg_meta = arg_meta or {}
                    prop = {
                        "type": "string",
                        "description": arg_meta.get("description", f"Parameter {arg_name}"),
                    }
                    if arg_meta.get("options"):
                        prop["enum"] = [str(o) for o in arg_meta["options"]]
                    properties[arg_name] = prop
                    required.append(arg_name)

            tools.append(
                {
                    "name": mcp_name,
                    "description": full_desc,
                    "inputSchema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
            )

        return tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        arguments = arguments or {}

        if name == "witchcraft_system_stats":
            stats = get_system_metrics()
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(stats, indent=2),
                    }
                ],
                "isError": False,
            }

        if name == "witchcraft_search_binds":
            query = str(arguments.get("query", "")).lower().strip()
            category = str(arguments.get("category", "")).lower().strip()
            cmd_backend = str(arguments.get("cmd_backend", "")).lower().strip()

            matches = []
            for bind in self.db:
                b_name = str(bind.get("name", ""))
                b_desc = str(bind.get("description", ""))
                b_cat = str(bind.get("category", ""))
                b_back = str(bind.get("cmd_backend", ""))

                if query and query not in b_name.lower() and query not in b_desc.lower():
                    continue
                if category and category != b_cat.lower():
                    continue
                if cmd_backend and cmd_backend != b_back.lower():
                    continue

                matches.append(
                    {
                        "name": b_name,
                        "mcp_tool": _sanitize_tool_name(b_name),
                        "category": b_cat,
                        "cmd_backend": b_back,
                        "description": b_desc,
                        "command": bind.get("command"),
                        "arguments": list((bind.get("arguments") or {}).keys()),
                    }
                )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"total": len(matches), "results": matches},
                            indent=2,
                        ),
                    }
                ],
                "isError": False,
            }

        if name == "witchcraft_xcript_eval":
            return self._run_xcript(arguments)

        bind = self._tool_map.get(name)
        if not bind:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Unknown tool '{name}'. Use witchcraft_search_binds to list available tools.",
                    }
                ],
                "isError": True,
            }

        cmd_template = str(bind.get("command", ""))
        bind_args = bind.get("arguments") or {}
        cmd = cmd_template

        for arg_name in bind_args:
            if arg_name not in arguments or arguments[arg_name] is None:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Missing required argument '{arg_name}' for bind '{bind.get('name')}'.",
                        }
                    ],
                    "isError": True,
                }
            val = str(arguments[arg_name])
            cmd = cmd.replace(f"@@{arg_name}", val)

        # If bind is a native witchcraft function in FN_REGISTRY, run via main.py
        if bind.get("cmd_backend") == "witchcraft":
            return self._run_native_bind(bind, arguments)

        result = net_exec(cmd)
        payload = {
            "bind": bind.get("name"),
            "cmd_backend": bind.get("cmd_backend"),
            "executed_command": cmd,
            "status": result.get("status"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
        }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2),
                }
            ],
            "isError": result.get("status", 0) != 0,
        }

    def _run_native_bind(self, bind: dict, arguments: dict) -> dict:
        bind_name = bind.get("name", "").replace("wfex.", "")
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        main_py = os.path.join(project_root, "main.py")

        cli_args = [sys.executable, main_py, bind_name, "--output_mode_none"]
        for k, v in arguments.items():
            cli_args.extend([f"--{k}", str(v)])

        proc = subprocess.run(
            cli_args,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        payload = {
            "bind": bind.get("name"),
            "cmd_backend": "witchcraft",
            "status": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2),
                }
            ],
            "isError": proc.returncode != 0,
        }

    def _run_xcript(self, arguments: dict) -> dict:
        monorepo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../..")
        )
        xcript_bin = os.path.join(monorepo_root, "xcript", "target", "release", "xcript")
        if not os.path.isfile(xcript_bin):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Xcript static binary not found at '{xcript_bin}'. Build it with 'cargo build --release' in xcript/.",
                    }
                ],
                "isError": True,
            }

        code = arguments.get("code")
        file_path = arguments.get("file")
        if code:
            cmd = [xcript_bin, "-e", str(code)]
        elif file_path:
            cmd = [xcript_bin, str(file_path)]
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Provide either 'code' or 'file' to witchcraft_xcript_eval.",
                    }
                ],
                "isError": True,
            }

        proc = subprocess.run(
            cmd,
            cwd=monorepo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        payload = {
            "cmd_backend": "xcript",
            "status": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2),
                }
            ],
            "isError": proc.returncode != 0,
        }

    def get_resources(self) -> list:
        return [
            {
                "uri": "witchcraft://database/rocketdb",
                "name": "WitchcraftFEX RocketDB v2",
                "description": "Complete catalog of WitchcraftFEX binds, arguments, categories, and cmd_backend.",
                "mimeType": "application/json",
            },
            {
                "uri": "witchcraft://manual/manual.txt",
                "name": "WitchcraftFEX Manual",
                "description": "Official manual and architecture documentation for WitchcraftFEX.",
                "mimeType": "text/plain",
            },
            {
                "uri": "witchcraft://system/stats",
                "name": "Live System Telemetry",
                "description": "Real-time OS, CPU, RAM, GPU, container, VM, and network stats.",
                "mimeType": "application/json",
            },
        ]

    def read_resource(self, uri: str) -> dict:
        if uri == "witchcraft://database/rocketdb":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps({"index": self.db}, indent=2),
                    }
                ]
            }
        if uri == "witchcraft://manual/manual.txt":
            manual_path = os.path.join(NT_DATAROOT, "manual", "manual.txt")
            text = ""
            if os.path.isfile(manual_path):
                with open(manual_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": text,
                    }
                ]
            }
        if uri == "witchcraft://system/stats":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(get_system_metrics(), indent=2),
                    }
                ]
            }
        raise ValueError(f"Resource not found: {uri}")

    def get_prompts(self) -> list:
        return [
            {
                "name": "opsec_recon",
                "description": "Perform structured reconnaissance on a target domain or IP using WitchcraftFEX.",
                "arguments": [
                    {
                        "name": "target",
                        "description": "Target domain or IPv4 address",
                        "required": True,
                    }
                ],
            },
            {
                "name": "xcript_automation",
                "description": "Generate and execute a flat Witchcraft-Xcript (.xcript) automation playbook.",
                "arguments": [
                    {
                        "name": "task",
                        "description": "Automation objective to implement in Xcript",
                        "required": True,
                    }
                ],
            },
        ]

    def get_prompt(self, name: str, arguments: dict) -> dict:
        arguments = arguments or {}
        if name == "opsec_recon":
            target = arguments.get("target", "<target>")
            return {
                "description": f"OPSEC Reconnaissance workflow for {target}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Run a reconnaissance workflow on target '{target}' using WitchcraftFEX MCP tools:\n"
                                "1. Search relevant recon binds with witchcraft_search_binds (category: 'network' or 'security').\n"
                                "2. Run DNS/WHOIS/IP checks (e.g., scanner_dns, scanner_ip, net_whois).\n"
                                "3. Summarize findings in a structured report."
                            ),
                        },
                    }
                ],
            }
        if name == "xcript_automation":
            task = arguments.get("task", "<task>")
            return {
                "description": f"Xcript automation generator for: {task}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Write and execute a flat Xcript script for the task: '{task}'.\n"
                                "Use only valid Xcript constructs (declare, echo, warn, table[], while..until, for..in, if/elif/else/default, analyse, exec) "
                                "and run it via witchcraft_xcript_eval."
                            ),
                        },
                    }
                ],
            }
        raise ValueError(f"Prompt not found: {name}")

    def handle_request(self, message: dict) -> dict | None:
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}

        # Notifications have no 'id' and expect no response
        if msg_id is None:
            return None

        try:
            if method == "initialize":
                client_version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
                result = {
                    "protocolVersion": client_version,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "witchcraft-fex-mcp",
                        "version": NT_VERSION,
                    },
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self.get_tools()}
            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments") or {}
                # Capture any stray stdout during tool execution so stdio JSON-RPC stays clean
                buf_out = io.StringIO()
                buf_err = io.StringIO()
                with redirect_stdout(buf_out), redirect_stderr(buf_err):
                    result = self.call_tool(tool_name, tool_args)
            elif method == "resources/list":
                result = {"resources": self.get_resources()}
            elif method == "resources/templates/list":
                result = {"resourceTemplates": []}
            elif method == "resources/read":
                uri = params.get("uri", "")
                result = self.read_resource(uri)
            elif method == "prompts/list":
                result = {"prompts": self.get_prompts()}
            elif method == "prompts/get":
                p_name = params.get("name", "")
                p_args = params.get("arguments") or {}
                result = self.get_prompt(p_name, p_args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": str(exc),
                },
            }

    def serve_stdio(self):
        """Run the MCP JSON-RPC loop over standard input/output."""
        while True:
            line = sys.stdin.readline()
            if not line:
                break

            stripped = line.strip()
            if not stripped:
                continue

            # Support both Content-Length framed and newline-delimited JSON-RPC
            if stripped.lower().startswith("content-length:"):
                length = int(stripped.split(":", 1)[1].strip())
                # Read until empty header separator line
                while True:
                    hdr = sys.stdin.readline()
                    if not hdr or hdr.strip() == "":
                        break
                body = sys.stdin.read(length)
                try:
                    msg = json.loads(body)
                except json.JSONDecodeError:
                    continue
                resp = self.handle_request(msg)
                if resp is not None:
                    out_bytes = json.dumps(resp).encode("utf-8")
                    sys.stdout.write(f"Content-Length: {len(out_bytes)}\r\n\r\n")
                    sys.stdout.write(out_bytes.decode("utf-8"))
                    sys.stdout.flush()
            else:
                try:
                    msg = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                resp = self.handle_request(msg)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()


def mcp_server_wrapper(args_v=None):
    out_stream = sys.stdout if sys.stdin.isatty() else sys.stderr
    with redirect_stdout(out_stream):
        net_logger(SPIDER, "magenta", "bold", False)
        net_logger("Running MCP Server use CTRL + c to stop", "white", "bold", False)

    server = WitchcraftMCPServer()
    server.serve_stdio()
    return 0
