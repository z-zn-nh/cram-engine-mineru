import unittest

from app.backend.cram_app.mindmap import (
    count_nodes,
    normalize_root,
    parse_outline,
    to_markdown,
    to_markmap_html,
    to_opml,
    validate_mindmap,
)


SAMPLE = """# 采样定理
- 核心结论
  - 采样率≥2倍最高频率
  - 奈奎斯特频率
- 混叠
  - 成因
  - 抗混叠滤波
"""


class MindmapTests(unittest.TestCase):
    def _tree(self, text: str, topic: str = "采样定理"):
        return normalize_root(parse_outline(text), topic)

    def test_parse_and_validate_ok(self):
        root = self._tree(SAMPLE)
        self.assertEqual(root.label, "采样定理")
        self.assertEqual(validate_mindmap(root), [])
        self.assertGreaterEqual(count_nodes(root), 6)

    def test_validate_flags_flat_or_tiny(self):
        self.assertTrue(validate_mindmap(self._tree("就一行没有结构", "x")))

    def test_to_markdown_keeps_structure(self):
        md = to_markdown(self._tree(SAMPLE))
        self.assertTrue(md.startswith("# 采样定理"))
        self.assertIn("  - 采样率≥2倍最高频率", md)  # 2-space nesting
        self.assertEqual(count_nodes(self._tree(SAMPLE)), count_nodes(self._tree(md)))

    def test_parses_mixed_headings_and_bullets(self):
        root = self._tree("# 根\n## 第一章\n- 点A\n## 第二章\n", "根")
        labels = [child.label for child in root.children]
        self.assertIn("第一章", labels)
        self.assertIn("第二章", labels)

    def test_strips_markdown_marks_in_labels(self):
        root = self._tree("# 根\n- **加粗点** [来源](x.pdf)\n", "根")
        self.assertEqual(root.children[0].label, "加粗点 来源")

    def test_opml_is_nested_xml(self):
        opml = to_opml(self._tree(SAMPLE), "采样定理")
        self.assertIn("<opml", opml)
        self.assertIn('text="采样定理"', opml)
        self.assertIn('text="混叠"', opml)
        self.assertEqual(opml.count("<outline"), count_nodes(self._tree(SAMPLE)) + 1)

    def test_markmap_html_embeds_markdown(self):
        html = to_markmap_html("# 采样定理\n- 混叠\n", "采样定理")
        self.assertIn("markmap-autoloader", html)
        self.assertIn("text/template", html)
        self.assertIn("采样定理", html)


if __name__ == "__main__":
    unittest.main()
