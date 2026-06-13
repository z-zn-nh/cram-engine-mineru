import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class InstallSkillTests(unittest.TestCase):
    def test_install_script_copies_skill_files_to_custom_root(self):
        with TemporaryDirectory() as tmp:
            target_root = Path(tmp) / "skills"
            command = [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts/install-skill.ps1",
                "-TargetRoot",
                str(target_root),
            ]

            completed = subprocess.run(command, check=False, capture_output=True)

            self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
            installed = target_root / "cram-engine-mineru"
            self.assertTrue((installed / "SKILL.md").exists())
            self.assertTrue((installed / "stages" / "stage0-ingest.md").exists())
            self.assertTrue((installed / "scripts" / "ingest_materials.py").exists())
            self.assertFalse((installed / ".git").exists())
            self.assertFalse((installed / "tests").exists())


if __name__ == "__main__":
    unittest.main()
