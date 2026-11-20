import json
import os
import re
import urllib.error
import urllib.request
import uuid

from witchcraft.metalcore.core import SPIDER, net_logger, search_arg
from witchcraft.interface.mcp.mcp_server import WitchcraftMCPServer

HARPIA_LLM_URL = os.getenv("NT_HARPIA_URL", "http://localhost:5599/v1/chat/completions")
DEFAULT_MAX_STEPS = int(os.getenv("NT_HARPIA_MAX_STEPS", "8"))
DEFAULT_SHELL_MODE = os.getenv("NT_HARPIA_SHELL_MODE", "propose")
LLM_SUMMARY_TRUNCATE_HEAD = 1000
LLM_SUMMARY_TRUNCATE_TAIL = 1000
SHELL_TOOL_NAMES = {"witchcraft_shell_exec", "bash"}

HARPIA_SYSTEM_PROMPT = (
    "You are Harpia, an autonomous cybersecurity and OPSEC AI agent embedded in WitchcraftFEX.\n"
    "OPERATING RULES:\n"
    "1. NEVER invent, fake, simulate, or hallucinate command execution, scan results, or terminal output.\n"
    "2. If a required argument (domain, IP, file, interface) is missing and cannot be discovered via tools, ask the user.\n"
    "3. You operate in a multi-step loop. You may chain multiple MCP tools across steps until the goal is complete.\n"
    "4. If the right bind is not in your current tool list, call witchcraft_search_binds first to discover it.\n"
    "5. If no MCP bind covers the task (e.g. pipes, grep/awk, custom shell commands), call witchcraft_shell_exec "
    "with 'command' and 'reason'. In propose mode the operator will approve it before execution.\n"
    "6. Emit tool calls using native tool_calls or the exact block:\n"
    "<tool_call>{\"name\": \"<tool_name>\", \"arguments\": {<key>: <value>}}</tool_call>\n"
    "7. When all needed steps are done, provide a concise final summary based strictly on the real tool outputs."
)

_PENDING_SESSIONS = {}


def select_relevant_tools(mcp: WitchcraftMCPServer, prompt: str, limit: int = 10, shell_mode: str = DEFAULT_SHELL_MODE) -> list:
    all_tools = mcp.get_tools()
    core_names = {
        "witchcraft_system_stats",
        "witchcraft_search_binds",
        "witchcraft_xcript_eval",
    }
    if shell_mode != "off":
        core_names.add("witchcraft_shell_exec")

    selected = [t for t in all_tools if t["name"] in core_names]

    words = [w.lower() for w in re.findall(r"[a-zA-Z0-9_.-]+", prompt) if len(w) >= 2]
    scored = []
    for tool in all_tools:
        if tool["name"] in core_names:
            continue
        if shell_mode == "off" and tool["name"] in SHELL_TOOL_NAMES:
            continue
        haystack = f"{tool['name']} {tool.get('description', '')}".lower()
        score = sum(2 if w in tool["name"].lower() else 1 for w in words if w in haystack)
        if score > 0:
            scored.append((score, tool))

    scored.sort(key=lambda x: x[0], reverse=True)
    for _, tool in scored[:limit]:
        selected.append(tool)

    return selected


def _inject_discovered_tools(mcp: WitchcraftMCPServer, active_tools: list, search_output: str, max_total: int = 20) -> None:
    try:
        data = json.loads(search_output)
    except Exception:
        return
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list) or not results:
        return

    existing_names = {t["name"] for t in active_tools}
    discovered_names = [
        item.get("mcp_tool") for item in results if isinstance(item, dict) and item.get("mcp_tool")
    ]
    if not discovered_names:
        return

    catalog = {t["name"]: t for t in mcp.get_tools()}
    for name in discovered_names:
        if len(active_tools) >= max_total:
            break
        if name not in existing_names and name in catalog:
            active_tools.append(catalog[name])
            existing_names.add(name)


def _format_tools_summary(tools: list) -> str:
    return "\n".join(
        f"- {t['name']}: {t.get('description', '')} | args: {list(t.get('inputSchema', {}).get('properties', {}).keys())}"
        for t in tools
    )


def _build_system_message(tools: list, shell_mode: str) -> dict:
    return {
        "role": "system",
        "content": (
            f"{HARPIA_SYSTEM_PROMPT}\n"
            f"Current shell_mode: {shell_mode}\n\n"
            f"Available MCP Tools:\n{_format_tools_summary(tools)}"
        ),
    }


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


def _decode_json_objects(text: str) -> list:
    decoder = json.JSONDecoder()
    objects = []
    idx = 0
    length = len(text)
    while idx < length:
        brace = text.find("{", idx)
        if brace == -1:
            break
        try:
            obj, end = decoder.raw_decode(text, brace)
            if isinstance(obj, dict):
                objects.append(obj)
            idx = end
        except Exception:
            idx = brace + 1
    return objects


def _extract_inline_tool_calls(text: str) -> list:
    calls = []
    tag_patterns = [
        r"<tool_call>(.*?)</tool_call>",
        r"<SCRATCHPAD>(.*?)</SCRATCHPAD>",
        r"<scratchpad>(.*?)</scratchpad>",
        r"```(?:json)?\s*(.*?)```",
    ]
    matched_blocks = []
    for pat in tag_patterns:
        for m in re.finditer(pat, text, re.DOTALL):
            matched_blocks.append(m.group(1))

    sources = matched_blocks if matched_blocks else [text]
    for src in sources:
        for obj in _decode_json_objects(src):
            name = obj.get("name") or obj.get("tool")
            if isinstance(name, str) and name.strip():
                args = obj.get("arguments")
                if args is None:
                    args = obj.get("args")
                if not isinstance(args, dict):
                    args = {}
                calls.append({"name": name.strip(), "arguments": args})
    return calls


def _extract_inline_tool_call(text: str) -> dict | None:
    calls = _extract_inline_tool_calls(text)
    return calls[0] if calls else None


def _format_output_for_llm(raw_output: str, head: int = LLM_SUMMARY_TRUNCATE_HEAD, tail: int = LLM_SUMMARY_TRUNCATE_TAIL) -> str:
    clean = raw_output or ""
    try:
        parsed = json.loads(clean)
        if isinstance(parsed, dict) and ("stdout" in parsed or "stderr" in parsed):
            parts = []
            if parsed.get("executed_command"):
                parts.append(f"command: {parsed['executed_command']}")
            if parsed.get("status") is not None:
                parts.append(f"status: {parsed['status']}")
            stdout = re.sub(r"<[^>]+>", "", str(parsed.get("stdout", "")))
            stderr = re.sub(r"<[^>]+>", "", str(parsed.get("stderr", "")))
            if stdout:
                parts.append(f"stdout:\n{stdout}")
            if stderr:
                parts.append(f"stderr:\n{stderr}")
            clean = "\n".join(parts)
    except Exception:
        clean = re.sub(r"<[^>]+>", "", clean)

    if len(clean) > head + tail + 64:
        omitted = len(clean) - (head + tail)
        clean = f"{clean[:head]}\n... [{omitted} chars truncated for LLM summary context; full output was printed to operator] ...\n{clean[-tail:]}"
    return clean


def _extract_command_from_shell_args(c_name: str, c_args: dict) -> tuple:
    cmd = str(c_args.get("command", "")).strip()
    reason = str(c_args.get("reason", "")).strip()
    return cmd, reason


def _execute_and_record(
    mcp: WitchcraftMCPServer,
    c_name: str,
    c_args: dict,
    executed_tools: list,
    active_tools: list,
    messages: list,
    on_tool_output=None,
) -> None:
    res = mcp.call_tool(c_name, c_args)
    out_text = "".join(item.get("text", "") for item in res.get("content", []))
    record = {
        "name": c_name,
        "arguments": c_args,
        "output": out_text,
        "isError": res.get("isError", False),
    }
    executed_tools.append(record)
    if on_tool_output:
        on_tool_output(record)

    if c_name == "witchcraft_search_binds" and not record["isError"]:
        _inject_discovered_tools(mcp, active_tools, out_text)
        messages[0] = _build_system_message(active_tools, _extract_shell_mode_from_system(messages[0]))

    llm_obs = _format_output_for_llm(out_text)
    messages.append(
        {
            "role": "user",
            "content": (
                f"[Observation from '{c_name}']:\n{llm_obs}\n\n"
                "If more steps are needed to fulfill the operator's request, emit the next tool call. "
                "Otherwise, provide the final summary."
            ),
        }
    )


def _extract_shell_mode_from_system(sys_msg: dict) -> str:
    m = re.search(r"Current shell_mode:\s*(\w+)", str(sys_msg.get("content", "")))
    return m.group(1) if m else DEFAULT_SHELL_MODE


def _run_agent_loop(
    mcp: WitchcraftMCPServer,
    messages: list,
    active_tools: list,
    executed_tools: list,
    seen_calls: set,
    step: int,
    max_steps: int,
    shell_mode: str,
    llm_url: str = None,
    on_tool_output=None,
    approval_callback=None,
    pending_calls: list = None,
) -> dict:
    final_content = ""
    queue = list(pending_calls or [])

    try:
        while step < max_steps:
            if not queue:
                try:
                    completion = _call_llama_completion(messages, tools=active_tools, llm_url=llm_url)
                except Exception:
                    completion = _call_llama_completion(messages, tools=None, llm_url=llm_url)

                choice = (completion.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                content = msg.get("content") or ""
                native_calls = msg.get("tool_calls") or []

                parsed_calls = []
                for tc in native_calls:
                    fn = tc.get("function") or {}
                    raw_args = fn.get("arguments") or "{}"
                    try:
                        args_dict = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args_dict = {}
                    if fn.get("name"):
                        parsed_calls.append({"name": fn["name"], "arguments": args_dict or {}})

                if not parsed_calls:
                    parsed_calls = _extract_inline_tool_calls(content)

                if not parsed_calls:
                    final_content = content
                    break

                messages.append({"role": "assistant", "content": content or f"Calling {[c['name'] for c in parsed_calls]}"})
                queue = parsed_calls

            while queue:
                call = queue.pop(0)
                c_name = call["name"]
                c_args = call.get("arguments") or {}

                call_key = (c_name, json.dumps(c_args, sort_keys=True, ensure_ascii=False))
                if call_key in seen_calls:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"[Notice] Tool '{c_name}' was already executed with identical arguments. "
                                "Use the previous observation, choose a different step, or provide the final answer."
                            ),
                        }
                    )
                    continue
                seen_calls.add(call_key)

                if c_name in SHELL_TOOL_NAMES:
                    if shell_mode == "off":
                        messages.append(
                            {
                                "role": "user",
                                "content": "[Policy] Raw shell execution is disabled (shell_mode=off). Use an MCP bind instead or inform the operator.",
                            }
                        )
                        continue

                    cmd, reason = _extract_command_from_shell_args(c_name, c_args)
                    if shell_mode == "propose":
                        if approval_callback is not None:
                            approved, final_cmd = approval_callback(cmd, reason)
                            if not approved:
                                messages.append(
                                    {
                                        "role": "user",
                                        "content": f"[Operator Rejected] Raw shell command '{cmd}' was rejected. Propose another approach or stop.",
                                    }
                                )
                                continue
                            c_args = dict(c_args)
                            c_args["command"] = final_cmd
                            c_name = "witchcraft_shell_exec"
                        else:
                            session_id = uuid.uuid4().hex
                            pending_action = {
                                "tool": "witchcraft_shell_exec",
                                "command": cmd,
                                "reason": reason,
                                "arguments": c_args,
                            }
                            _PENDING_SESSIONS[session_id] = {
                                "messages": messages,
                                "active_tools": active_tools,
                                "executed_tools": executed_tools,
                                "seen_calls": seen_calls,
                                "remaining_calls": queue,
                                "step": step,
                                "max_steps": max_steps,
                                "shell_mode": shell_mode,
                                "llm_url": llm_url,
                                "pending_action": pending_action,
                            }
                            return {
                                "status": "awaiting_approval",
                                "session_id": session_id,
                                "pending_action": pending_action,
                                "reply": f"Awaiting operator approval to execute raw shell command:\n{cmd}",
                                "tool_calls": executed_tools,
                                "steps": step,
                            }

                _execute_and_record(
                    mcp=mcp,
                    c_name=c_name,
                    c_args=c_args,
                    executed_tools=executed_tools,
                    active_tools=active_tools,
                    messages=messages,
                    on_tool_output=on_tool_output,
                )

            step += 1
        else:
            follow_up = _call_llama_completion(messages, tools=None, llm_url=llm_url)
            final_content = ((follow_up.get("choices") or [{}])[0].get("message") or {}).get("content", "")

        return {
            "status": "ok",
            "reply": (final_content or "").strip(),
            "tool_calls": executed_tools,
            "steps": step,
        }

    except urllib.error.URLError as exc:
        return {
            "status": "offline",
            "reply": (
                f"[Harpia LLM Offline] Could not reach local llama-server at {llm_url or HARPIA_LLM_URL} ({exc.reason}).\n"
                "Start it with: ./main.py server.harpia --host localhost --port 5599 --model spellbook/models/model.gguf\n"
                "Tip: You can still run tools directly using `/mcp <tool> <json>`, `/xcript <code>`, or `/shell <cmd>`."
            ),
            "tool_calls": executed_tools,
            "steps": step,
        }
    except Exception as exc:
        return {
            "status": "error",
            "reply": f"[Harpia Error] {exc}",
            "tool_calls": executed_tools,
            "steps": step,
        }


def harpia_resume_approval(
    session_id: str,
    approved: bool,
    edited_command: str = None,
    on_tool_output=None,
    approval_callback=None,
) -> dict:
    session = _PENDING_SESSIONS.pop(session_id, None)
    if not session:
        return {
            "status": "error",
            "reply": f"Session '{session_id}' not found or already resolved.",
            "tool_calls": [],
            "steps": 0,
        }

    mcp = WitchcraftMCPServer()
    pending = session["pending_action"]
    messages = session["messages"]
    active_tools = session["active_tools"]
    executed_tools = session["executed_tools"]

    if approved:
        final_cmd = (edited_command if edited_command is not None else pending["command"]).strip()
        args = {"command": final_cmd, "reason": pending.get("reason", "")}
        _execute_and_record(
            mcp=mcp,
            c_name="witchcraft_shell_exec",
            c_args=args,
            executed_tools=executed_tools,
            active_tools=active_tools,
            messages=messages,
            on_tool_output=on_tool_output,
        )
    else:
        messages.append(
            {
                "role": "user",
                "content": f"[Operator Rejected] Raw shell command '{pending['command']}' was rejected. Propose another approach or stop.",
            }
        )

    return _run_agent_loop(
        mcp=mcp,
        messages=messages,
        active_tools=active_tools,
        executed_tools=executed_tools,
        seen_calls=session["seen_calls"],
        step=session["step"] + (0 if session["remaining_calls"] else 1),
        max_steps=session["max_steps"],
        shell_mode=session["shell_mode"],
        llm_url=session["llm_url"],
        on_tool_output=on_tool_output,
        approval_callback=approval_callback,
        pending_calls=session["remaining_calls"],
    )


def harpia_chat(
    prompt: str,
    history: list = None,
    llm_url: str = None,
    direct_tool: dict = None,
    max_steps: int = None,
    shell_mode: str = None,
    on_tool_output=None,
    approval_callback=None,
) -> dict:
    mcp = WitchcraftMCPServer()
    executed_tools = []
    eff_max_steps = max_steps if isinstance(max_steps, int) and max_steps > 0 else DEFAULT_MAX_STEPS
    eff_shell_mode = (shell_mode or DEFAULT_SHELL_MODE).lower()
    if eff_shell_mode not in ("propose", "auto", "off"):
        eff_shell_mode = "propose"

    if direct_tool and isinstance(direct_tool, dict) and direct_tool.get("name"):
        t_name = direct_tool["name"]
        t_args = direct_tool.get("arguments") or {}
        res = mcp.call_tool(t_name, t_args)
        out_text = "".join(item.get("text", "") for item in res.get("content", []))
        record = {
            "name": t_name,
            "arguments": t_args,
            "output": out_text,
            "isError": res.get("isError", False),
        }
        executed_tools.append(record)
        if on_tool_output:
            on_tool_output(record)
        return {
            "status": "ok",
            "reply": out_text,
            "tool_calls": executed_tools,
            "steps": 1,
        }

    stripped = (prompt or "").strip()
    if stripped.startswith("/xcript "):
        code = stripped[len("/xcript ") :].strip()
        res = mcp.call_tool("witchcraft_xcript_eval", {"code": code})
        out_text = res["content"][0]["text"]
        record = {
            "name": "witchcraft_xcript_eval",
            "arguments": {"code": code},
            "output": out_text,
            "isError": res.get("isError", False),
        }
        executed_tools.append(record)
        if on_tool_output:
            on_tool_output(record)
        return {
            "status": "ok",
            "reply": out_text,
            "tool_calls": executed_tools,
            "steps": 1,
        }

    if stripped.startswith("/shell ") or stripped.startswith("!"):
        cmd = stripped[len("/shell ") :].strip() if stripped.startswith("/shell ") else stripped[1:].strip()
        res = mcp.call_tool("witchcraft_shell_exec", {"command": cmd, "reason": "Direct operator shell command"})
        out_text = res["content"][0]["text"]
        record = {
            "name": "witchcraft_shell_exec",
            "arguments": {"command": cmd},
            "output": out_text,
            "isError": res.get("isError", False),
        }
        executed_tools.append(record)
        if on_tool_output:
            on_tool_output(record)
        return {
            "status": "ok",
            "reply": out_text,
            "tool_calls": executed_tools,
            "steps": 1,
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
        record = {
            "name": t_name,
            "arguments": t_args,
            "output": out_text,
            "isError": res.get("isError", False),
        }
        executed_tools.append(record)
        if on_tool_output:
            on_tool_output(record)
        return {
            "status": "ok",
            "reply": out_text,
            "tool_calls": executed_tools,
            "steps": 1,
        }

    active_tools = select_relevant_tools(mcp, prompt, shell_mode=eff_shell_mode)
    messages = [_build_system_message(active_tools, eff_shell_mode)]

    if history and isinstance(history, list):
        for h in history[-10:]:
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append({"role": h["role"], "content": str(h["content"])})
    messages.append({"role": "user", "content": prompt})

    return _run_agent_loop(
        mcp=mcp,
        messages=messages,
        active_tools=active_tools,
        executed_tools=executed_tools,
        seen_calls=set(),
        step=0,
        max_steps=eff_max_steps,
        shell_mode=eff_shell_mode,
        llm_url=llm_url,
        on_tool_output=on_tool_output,
        approval_callback=approval_callback,
    )


def harpia_ask_wrapper(args_v=None):
    prompt = search_arg(args_v or [], "prompt")
    shell_mode = search_arg(args_v or [], "shell_mode") or DEFAULT_SHELL_MODE
    raw_steps = search_arg(args_v or [], "max_steps")
    max_steps = int(raw_steps) if raw_steps and str(raw_steps).isdigit() else DEFAULT_MAX_STEPS
    net_logger(SPIDER, "magenta", "bold", False)

    def _print_step(tc):
        net_logger(f"[MCP Tool] :: {tc['name']} ({tc['arguments']})", "cyan", "bold")
        net_logger(tc["output"], "white", "normal")

    result = harpia_chat(
        prompt,
        max_steps=max_steps,
        shell_mode=shell_mode,
        on_tool_output=_print_step,
    )
    net_logger(result.get("reply", ""), "green", "bold", True)
    return 0
