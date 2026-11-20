import json

from witchcraft.metalcore.core import SPIDER, net_logger
from witchcraft.interface.ai.harpia_agent import (
    DEFAULT_MAX_STEPS,
    DEFAULT_SHELL_MODE,
    _format_output_for_llm,
    harpia_chat,
)


def _print_tool_output(tc: dict) -> None:
    net_logger(f"[MCP Tool] {tc['name']} {tc.get('arguments', {})}", "cyan", "bold")
    raw = tc.get("output", "")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and ("stdout" in parsed or "stderr" in parsed):
            if parsed.get("executed_command"):
                net_logger(f"$ {parsed['executed_command']}", "yellow", "normal")
            if parsed.get("stdout"):
                print(parsed["stdout"], flush=True)
            if parsed.get("stderr"):
                net_logger(parsed["stderr"], "red", "normal")
            return
    except Exception:
        pass
    print(raw, flush=True)


def _prompt_shell_approval(command: str, reason: str) -> tuple:
    net_logger(f"[SHELL PROPOSTO] {command}", "yellow", "bold")
    if reason:
        net_logger(f"[MOTIVO] {reason}", "white", "normal")
    try:
        choice = input("Executar? [y/N/e(ditar)]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False, command

    if choice in ("y", "yes", "s", "sim"):
        return True, command
    if choice in ("e", "edit", "editar"):
        try:
            edited = input("Comando editado: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return False, command
        if edited:
            return True, edited
    return False, command


def harpia_cli_wrapper(args_v=None):
    net_logger(SPIDER, "magenta", "bold", False)
    net_logger("Harpia Agentic CLI (ReAct Loop + MCP Chaining + Pure Shell)", "cyan", "bold", False)
    net_logger(
        "Commands: /mode <agent|auto|off|shell>, /steps <N>, /shell <cmd>, !<cmd>, /mcp <tool> <json>, /xcript <code>, /clear, exit",
        "white",
        "normal",
        True,
    )

    history = []
    shell_mode = DEFAULT_SHELL_MODE
    direct_shell = False
    max_steps = DEFAULT_MAX_STEPS

    while True:
        prompt_label = "shell> " if direct_shell else f"harpia[{shell_mode}]> "
        try:
            user_input = input(prompt_label).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            net_logger("Exiting Harpia CLI...", "yellow", "bold")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
            net_logger("Exiting Harpia CLI...", "yellow", "bold")
            break
        if user_input.lower() == "/clear":
            history.clear()
            net_logger("History cleared.", "green", "normal")
            continue

        if user_input.lower().startswith("/mode "):
            mode = user_input.split(" ", 1)[1].strip().lower()
            if mode == "shell":
                direct_shell = True
                net_logger("Switched to PURE SHELL mode. Type /mode agent to return.", "yellow", "bold")
            elif mode in ("agent", "propose"):
                direct_shell = False
                shell_mode = "propose"
                net_logger("Switched to AGENT mode (shell_mode=propose).", "green", "bold")
            elif mode in ("auto", "off"):
                direct_shell = False
                shell_mode = mode
                net_logger(f"Switched to AGENT mode (shell_mode={shell_mode}).", "green", "bold")
            else:
                net_logger("Valid modes: agent, propose, auto, off, shell", "red", "normal")
            continue

        if user_input.lower().startswith("/steps "):
            val = user_input.split(" ", 1)[1].strip()
            if val.isdigit() and int(val) > 0:
                max_steps = int(val)
                net_logger(f"max_steps set to {max_steps}", "green", "normal")
            else:
                net_logger("Usage: /steps <positive integer>", "red", "normal")
            continue

        if direct_shell and not user_input.startswith("/"):
            harpia_chat(f"/shell {user_input}", on_tool_output=_print_tool_output)
            continue

        result = harpia_chat(
            user_input,
            history=history,
            max_steps=max_steps,
            shell_mode=shell_mode,
            on_tool_output=_print_tool_output,
            approval_callback=_prompt_shell_approval,
        )

        reply = result.get("reply", "")
        if reply:
            net_logger(f"Harpia: {reply}", "green", "bold", True)

        history.append({"role": "user", "content": user_input})
        if result.get("tool_calls"):
            calls_log = "\n".join(
                f"<tool_call>{json.dumps({'name': tc['name'], 'arguments': tc.get('arguments') or {}})}</tool_call>"
                for tc in result["tool_calls"]
            )
            compact_obs = "\n".join(
                f"[{tc['name']}]: {_format_output_for_llm(tc['output'], head=300, tail=300)}"
                for tc in result["tool_calls"]
            )
            history.append({"role": "assistant", "content": calls_log})
            history.append({"role": "user", "content": f"[Previous Observation]:\n{compact_obs}"})
        history.append({"role": "assistant", "content": reply})

    return 0
