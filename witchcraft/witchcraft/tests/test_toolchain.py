#░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░#
#                                                                                                                              #
#       Welcome to the WitchcraftFEX project! Originally written in Lua, the main parts of the codebase have been              #
#       rewritten in Python to make it easier to find new contributors and employees for the Cosmic Sec&Dev company.           #
#                                                                                                                              #
#░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░#

import subprocess
import sys
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
NETTRAVELER_PY = os.path.join(PROJECT_ROOT, "main.py")

class TestToolchain(unittest.TestCase):

    def test_version_command(self):
        cmd = [sys.executable, NETTRAVELER_PY, "version"]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("WitchcraftFEX", result.stdout)

    def test_wfex_output_modes(self):
        test_cases = [
            (["version", "--output_mode_html"], "<span"),
            (["version", "--output_mode_none"], "WitchcraftFEX"),
            (["version"], "WitchcraftFEX"),
        ]
        for args, expected in test_cases:
            with self.subTest(args=args):
                cmd = [sys.executable, NETTRAVELER_PY] + args
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=PROJECT_ROOT
                )
                self.assertIn(
                    expected,
                    result.stdout,
                    f"Expected '{expected}' in output for args {args}, but got:\n{result.stdout}"
                )

    def test_wfex_with_invalid_argument(self):
        random_arg = "invalid_subcommand_test_12345"
        cmd = [sys.executable, NETTRAVELER_PY, random_arg]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT
        )
        self.assertNotEqual(result.returncode, 0, "Expected non-zero exit code for invalid argument.")

if __name__ == "__main__":
    unittest.main()