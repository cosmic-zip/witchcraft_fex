import unittest
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if "NT_DATAROOT" not in os.environ:
    os.environ["NT_DATAROOT"] = os.path.join(PROJECT_ROOT, "spellbook/")

from spellbook.webui.builder import build_all_components, generate_tool_component

class TestWebGenerator(unittest.TestCase):

    def test_webui_index_contains_title(self):
        index_path = os.path.join(PROJECT_ROOT, "spellbook/webui/index.html")
        self.assertTrue(os.path.exists(index_path))
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("WitchcraftFEX", content)
        self.assertIn("sidebar", content.lower())

    def test_build_components(self):
        count = build_all_components()
        self.assertGreater(count, 0)
        sample_comp = os.path.join(PROJECT_ROOT, "spellbook/webui/components/tools/scanner.dns.html")
        self.assertTrue(os.path.exists(sample_comp))
        with open(sample_comp, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("scanner.dns", html)
        self.assertIn("tool-workspace-split", html)

if __name__ == "__main__":
    unittest.main()
