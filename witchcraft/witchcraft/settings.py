from witchcraft.interface.web.generator import gen_wrapper
from witchcraft.interface.mcp.mcp_server import mcp_server_wrapper
from witchcraft.interface.ai.harpia_agent import harpia_ask_wrapper
from witchcraft.interface.cli.interactive import harpia_cli_wrapper
from witchcraft.modules.genreport.reporter import gen_report_wrapper
from witchcraft.modules.osint.keyword_scanner import keyword_scanner_wrapper
from witchcraft.modules.osint.netcrawler import netcrawler_for_all_ipv4
from witchcraft.modules.scanner.dns import scanner_dns
from witchcraft.modules.scanner.ip_score import scanner_ip_score_addr
from witchcraft.modules.scanner.nmapper import nmapper
from witchcraft.modules.server.server import *
from witchcraft.modules.system.nt_stats import nt_stats_wrapper

FN_REGISTRY = {
    "scanner.keyword": keyword_scanner_wrapper,
    "scanner.netcrawler.ipv4": netcrawler_for_all_ipv4,
    "scanner.dns": scanner_dns,
    "scanner.ip": scanner_ip_score_addr,
    "scanner.nmapper": nmapper,
    "server": server_wrapper,
    "server.harpia": server_llama_wrapper,
    "server.default": server_default_wrapper,
    "server.minimal": server_minimal_wrapper,
    "server.mcp": mcp_server_wrapper,
    "harpia.mcp": mcp_server_wrapper,
    "harpia.cli": harpia_cli_wrapper,
    "harpia.ask": harpia_ask_wrapper,
    "build.web": gen_wrapper,
    "gen.report": gen_report_wrapper,
    "config.model": net_setup_default_model,
    "nt_stats": nt_stats_wrapper,
    "system.stats": nt_stats_wrapper,
}
