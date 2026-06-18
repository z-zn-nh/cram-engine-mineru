import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsContractTests(unittest.TestCase):
    def test_readme_documents_local_tui_start(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("OpenCode 风格 TUI", readme)
        self.assertIn("当前文件夹就是学科工作区", readme)
        self.assertIn("python D:\\cram-engine\\app\\backend\\cram.py", readme)
        self.assertIn(".cram", readme)
        self.assertIn("cram-output", readme)
        self.assertIn("z-zn-nh/cram-engine-mineru", readme)
        self.assertNotIn("npx skills add https://github.com/liuliu667/cram-engine", readme)
        self.assertNotIn("| `/cram <课程名> start`", readme)

    def test_skill_uses_fork_name_and_tui_trigger(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("name: cram-engine-mineru", skill)
        self.assertIn("OpenCode 风格 TUI", skill)
        self.assertIn("当前文件夹", skill)
        self.assertIn("长期记忆", skill)
        self.assertIn("/lint", skill)
        self.assertNotIn("name: cram-engine\n", skill)
        self.assertNotIn("使用 `/cram` 命令", skill)


if __name__ == "__main__":
    unittest.main()
