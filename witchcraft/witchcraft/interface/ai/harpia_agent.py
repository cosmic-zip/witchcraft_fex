import json
import os
import re
import urllib.error
import urllib.request

from witchcraft.metalcore.core import SPIDER, net_logger, search_arg
from witchcraft.interface.mcp.mcp_server import WitchcraftMCPServer

HARPIA_LLM_URL = os.getenv("NT_HARPIA_URL", "http://localhost:5599/v1/chat/completions")

HARPIA_SYSTEM_PROMPT = (
    "You are Harpia, the autonomous cybersecurity and OPSEC AI agent embedded in WitchcraftFEX.\n"
    "CRITICAL RULES:\n"
    "1. NEVER invent, fake, simulate, or hallucinate command execution, scan results, or terminal output.\n"
    "2. If the user asks for a scan, inspection, or action and the required argument (like a domain, IP, or file) is missing, DO NOT pretend you executed it. Immediately ask the user for the missing argument.\n"
    "3. When you have the required parameters to run a tool, you MUST emit a tool call block in the exact format:\n"
    "<tool_call>{\"name\": \"<tool_name>\", \"arguments\": {<key>: <value>}}</tool_call>\n"
    "4. Only discuss or summarize data after you have received the real tool output from the system."
)


def select_relevant_tools(mcp: WitchcraftMCPServer, prompt: str, limit: int = 12) -> list:
    """Select the most relevant MCP tools for the given prompt to fit local LLM context."""
    all_tools = mcp.get_tools()
    core_names = {
        "witchcraft_system_stats",
        "witchcraft_search_binds",
        "witchcraft_xcript_eval",
    }
    selected = [t for t in all_tools if t["name"] in core_names]

    words = [w.lower() for w in re.findall(r"[a-zA-Z0-9_.-]+", prompt) if len(w) >= 2]
    scored = []
    for tool in all_tools:
        if tool["name"] in core_names:
            continue
        haystack = f"{tool['name']} {tool.get('description', '')}".lower()
        score = sum(2 if w in tool["name"].lower() else 1 for w in words if w in haystack)
        if score > 0:
            scored.append((score, tool))

    scored.sort(key=lambda x: x[0], reverse=True)
    for _, tool in scored[:limit]:
        selected.append(tool)

    return selected


def _call_llama_completion(messages: list, tools: list = None, llm_url: str = None) -> dict:
    url = llm_url or HARPIA_LLM_URL
    payload = {
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False,
    }
    if tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_inline_tool_call(text: str) -> dict | None:
    patterns = [
        r"<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)",
        r"<SCRATCHPAD>\s*(\{.*?\})\s*(?:</SCRATCHPAD>|$)",
        r"<scratchpad>\s*(\{.*?\})\s*(?:</scratchpad>|$)",
        r"```(?:json)?\s*(\{\s*\"(?:name|tool)\"\s*:\s*\".*?\".*?\})\s*```",
        r"(\{\s*\"(?:name|tool)\"\s*:\s*\"[a-zA-Z0-9_.-]+\"\s*,\s*\"arguments\"\s*:\s*\{.*?\}\s*\})"
    ]
    for pat in patterns:
        match = re.search(pat, text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(1))
                if isinstance(obj, dict):
                    name = obj.get("name") or obj.get("tool")
                    if name:
                        return {
                            "name": name,
                            "arguments": obj.get("arguments") or obj.get("args") or {}
                        }
            except Exception:
                continue
    return None


def harpia_chat(
    prompt: str,
    history: list = None,
    llm_url: str = None,
    direct_tool: dict = None,
) -> dict:
    """
    Process a chat message through Harpia AI + Witchcraft MCP Server.
    Supports direct MCP tool invocation and local LLM agent loop with tool calling.
    """
    mcp = WitchcraftMCPServer()
    executed_tools = []

    # Direct MCP tool execution shortcut (e.g. from UI tool runner or `/mcp <tool> <json>`)
    if direct_tool and isinstance(direct_tool, dict) and direct_tool.get("name"):
        t_name = direct_tool["name"]
        t_args = direct_tool.get("arguments") or {}
        res = mcp.call_tool(t_name, t_args)
        out_text = ""
        for item in res.get("content", []):
            out_text += item.get("text", "")
        executed_tools.append(
            {
                "name": t_name,
                "arguments": t_args,
                "output": out_text,
                "isError": res.get("isError", False),
            }
        )
        return {
            "status": "ok",
            "reply": out_text,
            "tool_calls": executed_tools,
        }

    # Slash command in chat: `/tool <name> {"arg": "val"}` or `/xcript <code>`
    stripped = (prompt or "").strip()
    if stripped.startswith("/xcript "):
        code = stripped[len("/xcript ") :].strip()
        res = mcp.call_tool("witchcraft_xcript_eval", {"code": code})
        out_text = res["content"][0]["text"]
        executed_tools.append(
            {
                "name": "witchcraft_xcript_eval",
                "arguments": {"code": code},
                "output": out_text,
                "isError": res.get("isError", False),
            }
        )
        return {
            "status": "ok",
            "reply": out_text,
            "tool_calls": executed_tools,
        }

    if stripped.startswith("/mcp "):
        parts = stripped[len("/mcp ") :].strip().split(" ", 1)
        t_name = parts[0]
        t_args = {}
        if len(parts) > 1:
            try:
                t_args = json.loads(parts[1])
            except Exception:
                t_args = {"query": parts[1]}
        res = mcp.call_tool(t_name, t_args)
        out_text = res["content"][0]["text"]
        executed_tools.append(
            {
                "name": t_name,
                "arguments": t_args,
                "output": out_text,
                "isError": res.get("isError", False),
            }
        )
        return {
            "status": "ok",
            "reply": out_text,
            "tool_calls": executed_tools,
        }

    relevant_tools = select_relevant_tools(mcp, prompt)
    tools_summary = "\n".join(
        f"- {t['name']}: {t.get('description', '')} | args: {list(t.get('inputSchema', {}).get('properties', {}).keys())}"
        for t in relevant_tools
    )

    messages = [
        {
            "role": "system",
            "content": f"{HARPIA_SYSTEM_PROMPT}\n\nAvailable MCP Tools for this request:\n{tools_summary}",
        }
    ]
    if history and isinstance(history, list):
        for h in history[-8:]:
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append({"role": h["role"], "content": str(h["content"])})
    messages.append({"role": "user", "content": prompt})

    try:
        try:
            completion = _call_llama_completion(messages, tools=relevant_tools, llm_url=llm_url)
        except Exception:
            # Fallback without OpenAI 'tools' field if llama-server wasn't started with --jinja
            completion = _call_llama_completion(messages, tools=None, llm_url=llm_url)

        choice = (completion.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        # Check native OpenAI tool_calls or inline <tool_call>{...}</tool_call>
        parsed_calls = []
        for tc in tool_calls:
            fn = tc.get("function") or {}
            raw_args = fn.get("arguments") or "{}"
            args_dict = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            parsed_calls.append({"name": fn.get("name"), "arguments": args_dict})

        if not parsed_calls:
            inline = _extract_inline_tool_call(content)
            if inline:
                parsed_calls.append(
                    {
                        "name": inline.get("name"),
                        "arguments": inline.get("arguments") or {},
                    }
                )

        if parsed_calls:
            for call in parsed_calls:
                c_name = call["name"]
                c_args = call["arguments"]
                res = mcp.call_tool(c_name, c_args)
                out_text = res["content"][0]["text"]
                executed_tools.append(
                    {
                        "name": c_name,
                        "arguments": c_args,
                        "output": out_text,
                        "isError": res.get("isError", False),
                    }
                )
                # Sanitize output passed back to LLM context to prevent Bad Request (due to special tokens or HTML)
                summary_text = out_text
                try:
                    parsed_json = json.loads(out_text)
                    if isinstance(parsed_json, dict) and "stdout" in parsed_json:
                        raw_stdout = parsed_json["stdout"]
                        summary_text = re.sub(r"<[^>]+>", "", raw_stdout)
                except Exception:
                    pass

                messages.append({"role": "assistant", "content": content or f"Calling {c_name}"})
                messages.append(
                    {
                        "role": "user",
                        "content": f"[Tool Result for '{c_name}']:\n{summary_text[:1200]}\n\nSummarize the result cleanly for the operator.",
                    }
                )

            follow_up = _call_llama_completion(messages, tools=None, llm_url=llm_url)
            final_msg = ((follow_up.get("choices") or [{}])[0].get("message") or {}).get(
                "content", ""
            )
            content = final_msg or content

        return {
            "status": "ok",
            "reply": content.strip(),
            "tool_calls": executed_tools,
        }

    except urllib.error.URLError as exc:
        return {
            "status": "offline",
            "reply": (
                f"[Harpia LLM Offline] Could not reach local llama-server at {llm_url or HARPIA_LLM_URL} ({exc.reason}).\n"
                "Start it with: ./main.py server.harpia --host localhost --port 5599 --model spellbook/models/model.gguf\n"
                "Tip: You can still run MCP tools directly in this chat using `/mcp <tool_name> {\"arg\": \"val\"}` or `/xcript <code>`!"
            ),
            "tool_calls": executed_tools,
        }
    except Exception as exc:
        return {
            "status": "error",
            "reply": f"[Harpia Error] {exc}",
            "tool_calls": executed_tools,
        }


def harpia_ask_wrapper(args_v=None):
    prompt = search_arg(args_v or [], "prompt")
    net_logger(SPIDER, "magenta", "bold", False)
    result = harpia_chat(prompt)
    for tc in result.get("tool_calls", []):
        net_logger(f"[MCP Tool] :: {tc['name']} ({tc['arguments']})", "cyan", "bold")
        net_logger(tc["output"], "white", "normal")
    net_logger(result.get("reply", ""), "green", "bold", True)
    return 0

