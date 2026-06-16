import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AppStructureTests(unittest.TestCase):
    def test_app_workspace_exists(self):
        self.assertTrue((ROOT / "app").is_dir())
        self.assertTrue((ROOT / "app" / "frontend").is_dir())
        self.assertTrue((ROOT / "app" / "backend").is_dir())
        self.assertTrue((ROOT / "app" / "tauri").is_dir())

    def test_tauri_windows_icon_exists(self):
        icon = ROOT / "app" / "tauri" / "src-tauri" / "icons" / "icon.ico"

        self.assertTrue(icon.is_file())
        self.assertGreater(icon.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
