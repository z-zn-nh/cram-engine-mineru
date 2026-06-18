import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentSupportTests(unittest.TestCase):
    def test_agents_md_documents_tui_workflow_and_memory(self):
        content = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("cram-engine-mineru", content)
        self.assertIn("OpenCode 风格 TUI", content)
        self.assertIn("当前文件夹", content)
        self.assertIn(".cram", content)
        self.assertIn("cram-output", content)
        self.assertIn("长期记忆", content)

    def test_opencode_skill_and_command_exist(self):
        skill = ROOT / ".opencode" / "skills" / "cram-engine-mineru" / "SKILL.md"
        command = ROOT / ".opencode" / "commands" / "cram.md"

        self.assertTrue(skill.exists())
        self.assertTrue(command.exists())
        self.assertIn("OpenCode 风格 TUI", skill.read_text(encoding="utf-8"))
        self.assertIn("$ARGUMENTS", command.read_text(encoding="utf-8"))
        self.assertIn("cram-output", command.read_text(encoding="utf-8"))

    def test_install_script_copies_agents_and_opencode_files(self):
        install_script = (ROOT / "scripts" / "install-skill.ps1").read_text(encoding="utf-8")

        self.assertIn("AGENTS.md", install_script)
        self.assertIn(".opencode", install_script)


if __name__ == "__main__":
    unittest.main()
