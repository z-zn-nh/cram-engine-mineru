import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.ingest_materials import (
    SUPPORTED_EXTENSIONS,
    build_summary,
    check_environment,
    discover_materials,
    make_plan,
    safe_course_slug,
)


class IngestMaterialsTests(unittest.TestCase):
    def test_discovers_supported_materials_recursively(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "course"
            nested = root / "week1"
            nested.mkdir(parents=True)
            pdf = nested / "chapter1.pdf"
            pptx = root / "slides.pptx"
            image = root / "formula.png"
            ignored = root / "video.mp4"

            for path in [pdf, pptx, image, ignored]:
                path.write_text("placeholder", encoding="utf-8")

            materials = discover_materials([root])

            self.assertEqual([item.path for item in materials], [image, pptx, pdf])
            self.assertLessEqual(
                {item.path.suffix.lower() for item in materials},
                SUPPORTED_EXTENSIONS,
            )

    def test_make_plan_prefers_mineru_and_adds_ppt_pdf_fallback(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx = tmp_path / "lesson.pptx"
            pdf = tmp_path / "handout.pdf"
            image = tmp_path / "diagram.jpg"
            for path in [pptx, pdf, image]:
                path.write_text("placeholder", encoding="utf-8")

            plan = make_plan("通信原理", [pptx, pdf, image], output_root=tmp_path / "out")

            self.assertEqual(plan.course_slug, "通信原理")
            self.assertEqual(len(plan.jobs), 3)
            self.assertTrue(all(job.primary_engine == "mineru" for job in plan.jobs))
            self.assertEqual(plan.jobs[0].fallback_strategy, "libreoffice_pdf_then_mineru")
            self.assertIsNone(plan.jobs[1].fallback_strategy)
            self.assertEqual(plan.jobs[2].fallback_strategy, "pix2text_then_pix2tex")
            self.assertEqual(
                plan.summary_path,
                tmp_path / "out" / "通信原理" / "materials-summary.md",
            )

    def test_safe_course_slug_blocks_path_traversal(self):
        self.assertEqual(safe_course_slug(" ../组织/行为 学 "), "组织-行为-学")

    def test_build_summary_includes_source_and_strategy(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf = tmp_path / "chapter.pdf"
            pdf.write_text("placeholder", encoding="utf-8")
            plan = make_plan("组织行为学", [pdf], output_root=tmp_path / "out")

            summary = build_summary(plan)

            self.assertIn("# 组织行为学 资料摄取摘要", summary)
            self.assertIn("chapter.pdf", summary)
            self.assertIn("MinerU", summary)

    def test_check_environment_warns_about_windows_python_313(self):
        report = check_environment(
            "mineru",
            exists=lambda command: False,
            python_version=(3, 13),
            platform_name="win32",
        )

        self.assertIn("Python: 3.13", report)
        self.assertIn("Windows 建议使用 Python 3.10-3.12", report)
        self.assertIn("uv pip install -U \"mineru[all]\"", report)

    def test_check_environment_does_not_warn_when_mineru_exists_on_python_313(self):
        report = check_environment(
            "mineru",
            exists=lambda command: command == "mineru",
            python_version=(3, 13),
            platform_name="win32",
        )

        self.assertIn("Python: 3.13", report)
        self.assertIn("MinerU: OK", report)
        self.assertNotIn("Windows 建议使用 Python 3.10-3.12", report)


if __name__ == "__main__":
    unittest.main()
