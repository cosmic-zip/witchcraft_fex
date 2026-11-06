import unittest
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if "NT_DATAROOT" not in os.environ:
    os.environ["NT_DATAROOT"] = os.path.join(PROJECT_ROOT, "spellbook/")

from witchcraft.metalcore.core import (
    search_arg,
    net_exec,
    read_db,
    is_number,
    COLORS,
    COLORS_HTML
)

class TestMetalcore(unittest.TestCase):

    def test_search_arg_found(self):
        args = ["submodule", "--host", "127.0.0.1", "--port", "8080"]
        val = search_arg(args, "host")
        self.assertEqual(val, "127.0.0.1")

        port = search_arg(args, "port")
        self.assertEqual(port, "8080")

    def test_search_arg_not_found_optional(self):
        args = ["submodule", "--host", "127.0.0.1"]
        val = search_arg(args, "port", enforce_keyword=False)
        self.assertIsNone(val)

    def test_search_arg_enforce_missing(self):
        args = ["submodule", "--host", "127.0.0.1"]
        with self.assertRaises(SystemExit) as cm:
            search_arg(args, "missing_param", enforce_keyword=True)
        self.assertEqual(cm.exception.code, 128)

    def test_net_exec_echo(self):
        result = net_exec("echo 'hello witchcraft'")
        self.assertEqual(result["status"], 0)
        self.assertEqual(result["stdout"], "hello witchcraft")
        self.assertEqual(result["stderr"], "")

    def test_is_number(self):
        self.assertTrue(is_number("123"))
        self.assertTrue(is_number("123.45"))
        self.assertFalse(is_number("abc"))

    def test_read_db(self):
        db = read_db()
        self.assertIsInstance(db, list)
        self.assertGreater(len(db), 0, "Genesis database should contain registered items.")

if __name__ == "__main__":
    unittest.main()
