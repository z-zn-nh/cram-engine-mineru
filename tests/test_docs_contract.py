import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsContractTests(unittest.TestCase):
    def test_readme_uses_local_install_and_upload_start(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("scripts\\install-skill.ps1", readme)
        self.assertIn("期末速成：课程名", readme)
        self.assertIn("上传 PDF、PPT/PPTX 或图片", readme)
        self.assertIn("z-zn-nh/cram-engine-mineru", readme)
        self.assertNotIn("npx skills add https://github.com/liuliu667/cram-engine", readme)
        self.assertNotIn("| `/cram <课程名> start`", readme)

    def test_skill_uses_fork_name_and_upload_trigger(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("name: cram-engine-mineru", skill)
        self.assertIn("期末速成：<课程名>", skill)
        self.assertIn("优先使用用户上传的文件", skill)
        self.assertNotIn("name: cram-engine\n", skill)
        self.assertNotIn("使用 `/cram` 命令", skill)


if __name__ == "__main__":
    unittest.main()
