import unittest
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
os.chdir(PROJECT_ROOT)

if "NT_DATAROOT" not in os.environ:
    os.environ["NT_DATAROOT"] = os.path.join(PROJECT_ROOT, "spellbook/")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.discover(start_dir=os.path.join(PROJECT_ROOT, "witchcraft/tests"), top_level_dir=PROJECT_ROOT))
    suite.addTests(loader.discover(start_dir=os.path.join(PROJECT_ROOT, "spellbook/pkg/server"), top_level_dir=PROJECT_ROOT))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
