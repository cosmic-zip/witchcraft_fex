from witchcraft.metalcore.core import SPIDER, net_logger
from witchcraft.interface.ai.harpia_agent import harpia_chat


def harpia_cli_wrapper(args_v=None):
    """Interactive CLI chat session for Harpia AI + MCP tools."""
    net_logger(SPIDER, "magenta", "bold", False)
    net_logger("Harpia Interactive CLI (MCP + Xcript + Local LLM)", "cyan", "bold", False)
    net_logger("Commands: /mcp <tool> <json>, /xcript <code>, /clear, exit", "white", "normal", True)

    history = []
    while True:
        try:
            user_input = input("harpia> ").strip()
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

        result = harpia_chat(user_input, history=history)
        for tc in result.get("tool_calls", []):
            net_logger(f"[MCP Tool] {tc['name']} {tc['arguments']}", "cyan", "bold")
            net_logger(tc["output"], "white", "normal")

        reply = result.get("reply", "")
        net_logger(f"Harpia: {reply}", "green", "bold", True)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

    return 0

