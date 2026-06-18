import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TuiDocsTests(unittest.TestCase):
    def test_readme_documents_tui_as_primary_workflow(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("OpenCode 风格 TUI", readme)
        self.assertIn("当前文件夹就是学科工作区", readme)
        self.assertIn(".cram", readme)
        self.assertIn("cram-output", readme)
        self.assertIn("输出内容也会作为低优先级引用", readme)
        self.assertIn("/lint", readme)

    def test_agent_docs_no_longer_present_gui_as_primary_path(self):
        app_readme = (ROOT / "app" / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        for document in (app_readme, agents, skill):
            self.assertIn("OpenCode 风格 TUI", document)
            self.assertIn("当前文件夹", document)
            self.assertIn("长期记忆", document)
            self.assertIn("cram-output", document)


if __name__ == "__main__":
    unittest.main()
