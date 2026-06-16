import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesktopAppDocsTests(unittest.TestCase):
    def test_app_readme_documents_sidecar_and_three_pane_workflow(self):
        readme = (ROOT / "app" / "README.md").read_text(encoding="utf-8")

        self.assertIn("sidecar", readme)
        self.assertIn("build-sidecar.ps1", readme)
        self.assertIn("127.0.0.1:8000", readme)
        self.assertIn("左侧学科文件夹", readme)
        self.assertIn("右侧引用资料和产出结果", readme)

    def test_agent_docs_prefer_app_subject_folders_when_available(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        opencode = (ROOT / ".opencode" / "skills" / "cram-engine-mineru" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        for document in (agents, skill, opencode):
            self.assertIn("桌面 App", document)
            self.assertIn("学科文件夹", document)
            self.assertIn("产出结果", document)


if __name__ == "__main__":
    unittest.main()
