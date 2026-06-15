import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppStructureTests(unittest.TestCase):
    def test_app_workspace_exists(self):
        self.assertTrue((ROOT / "app").is_dir())
        self.assertTrue((ROOT / "app" / "frontend").is_dir())
        self.assertTrue((ROOT / "app" / "backend").is_dir())
        self.assertTrue((ROOT / "app" / "tauri").is_dir())


if __name__ == "__main__":
    unittest.main()
