import unittest
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if "NT_DATAROOT" not in os.environ:
    os.environ["NT_DATAROOT"] = os.path.join(PROJECT_ROOT, "spellbook/")

from witchcraft.modules.scanner.dns import scanner_dns
from witchcraft.modules.scanner.ip_score import scanner_ip_score_addr
from witchcraft.modules.scanner.nmapper import nmapper
from witchcraft.modules.osint.keyword_scanner import keyword_scanner_wrapper
from witchcraft.modules.osint.netcrawler import netcrawler_for_all_ipv4
from witchcraft.modules.genreport.reporter import gen_report_wrapper
from witchcraft.modules.system.nt_stats import get_system_metrics, nt_stats_wrapper

class TestModules(unittest.TestCase):

    def test_scanner_dns_wrapper_args(self):
        with self.assertRaises(SystemExit) as cm:
            scanner_dns(["scanner.dns"])
        self.assertEqual(cm.exception.code, 128)

    def test_ip_score_wrapper_args(self):
        with self.assertRaises(SystemExit) as cm:
            scanner_ip_score_addr(["scanner.ip"])
        self.assertEqual(cm.exception.code, 128)

    def test_keyword_scanner_wrapper_args(self):
        with self.assertRaises(SystemExit) as cm:
            keyword_scanner_wrapper(["scanner.keyword"])
        self.assertEqual(cm.exception.code, 128)

    def test_nt_stats_metrics(self):
        metrics = get_system_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn("cpu", metrics)
        self.assertIn("memory", metrics)
        self.assertIn("os", metrics)
        self.assertIn("uptime", metrics)
        self.assertIn("containers", metrics)
        self.assertIn("vms", metrics)
        self.assertIn("processes", metrics)
        self.assertIn("network", metrics)

    def test_nt_stats_wrapper_execution(self):
        status = nt_stats_wrapper(["system.stats", "--json", "true"])
        self.assertEqual(status, 0)

if __name__ == "__main__":
    unittest.main()
