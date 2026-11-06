import unittest
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if "NT_DATAROOT" not in os.environ:
    os.environ["NT_DATAROOT"] = os.path.join(PROJECT_ROOT, "spellbook/")

from witchcraft.interface.web.generator import gen_base, gen_extends

class TestWebGenerator(unittest.TestCase):

    def test_gen_base_contains_page_title(self):
        base_html = gen_base()
        self.assertIsInstance(base_html, str)
        self.assertIn("NettravalerEX", base_html)
        self.assertIn("sidebar", base_html.lower())

    def test_gen_extends_includes_extensions(self):
        extended_html = gen_extends()
        self.assertIsInstance(extended_html, str)
        self.assertNotIn("@@EXTENSIONS", extended_html, "Placeholder @@EXTENSIONS should be replaced.")
        self.assertNotIn("@@EXTENDS", extended_html, "Placeholder @@EXTENDS should be replaced.")

if __name__ == "__main__":
    unittest.main()
