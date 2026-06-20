import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesktopAppDocsTests(unittest.TestCase):
    def test_app_readme_documents_tui_as_primary_workflow(self):
        readme = (ROOT / "app" / "README.md").read_text(encoding="utf-8")

        self.assertIn("OpenCode 风格 TUI", readme)
        self.assertIn("不是桌面 GUI", readme)
        self.assertIn("当前文件夹就是学科工作区", readme)
        self.assertIn(".cram", readme)
        self.assertIn("cram-output", readme)
        self.assertIn("/lint", readme)

    def test_agent_docs_prefer_tui_folder_workspace(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        opencode = (ROOT / ".opencode" / "skills" / "cram-engine-mineru" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        trae_skill = (ROOT / ".trae" / "skills" / "cram-engine" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        trae_rules = (ROOT / ".trae" / "rules" / "project_rules.md").read_text(encoding="utf-8")

        for document in (agents, skill, opencode, trae_skill, trae_rules):
            self.assertIn("OpenCode 风格 TUI", document)
            self.assertIn("当前文件夹", document)
            self.assertIn("长期记忆", document)
            self.assertIn("cram-output", document)


if __name__ == "__main__":
    unittest.main()
