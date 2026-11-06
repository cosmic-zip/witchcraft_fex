import sys
import re
from witchcraft.metalcore.core import *

def nmapper(args_v: list):
    target = search_arg(args_v, "target")
    script = search_arg(args_v, "script", False)

    defstr = "sudo nmap -sS -sV -A --min-parallelis 16 --reason --script="

    if not script:
        script = "default"
    if script == "traveler":
        script = "default,safe,vuln"

    buffer = target.replace("http://", "").replace("https://", "").replace("www.", "")

    clean = buffer.replace(".", "")
    if is_number(clean):
        bind = f"{defstr}{script} {target}"
        net_logger(f"\n[namapper] :: Run IPv4 {target}", "cyan", "bold", True)
        net_logger(net_exec(bind).get('stdout'), "white")
        return 0

    if ":" in buffer:
        bind = f"{defstr}{script} {target} -6"
        net_logger(f"\n[namapper] :: Run IPv6 {target}", "cyan", "bold", True)
        net_logger(net_exec(bind).get('stdout'), "white")
        return 0

    iplist = net_exec(f"host {target} | grep -E 'has address|has IPv6 address' | awk '{{print $NF}}'")
    for ip in re.findall(r"[^\r\n]+", iplist.get('stdout')):
        if ":" in ip:
            bind = f"{defstr}{script} {ip} -6"
            net_logger(f"\n[namapper] :: Run IPv6 {ip}", "cyan", "bold", True)
            net_logger(net_exec(bind).get('stdout'), "white")
        else:
            bind = f"{defstr}{script} {ip}"
            net_logger(f"\n[namapper] :: Run IPv4 {ip}", "cyan", "bold", True)
            net_logger(net_exec(bind).get('stdout'), "white")

    return 0
