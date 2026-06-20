import tempfile
import unittest
from pathlib import Path

from app.backend.cram_app.teaching import (
    KnowledgePoint,
    TeachingSession,
    classify_teaching_input,
    clear_session,
    has_active_session,
    load_session,
    parse_tree,
    render_tree,
    save_session,
)
from app.backend.cram_app.workspace import CramWorkspace


class ParseTreeTests(unittest.TestCase):
    def test_parses_json_points_with_hooks(self):
        points = parse_tree('{"points": [{"title": "核心公式", "hook": "acronym"}, {"title": "三变量", "hook": "contrast"}]}')
        self.assertEqual([p.title for p in points], ["核心公式", "三变量"])
        self.assertEqual([p.hook for p in points], ["acronym", "contrast"])

    def test_parses_json_with_surrounding_prose(self):
        points = parse_tree('好的：\n{"points": [{"title": "采样定理"}]}\n以上。')
        self.assertEqual([p.title for p in points], ["采样定理"])
        self.assertEqual(points[0].hook, "none")  # missing hook defaults to none

    def test_invalid_hook_falls_back_to_none(self):
        points = parse_tree('{"points": [{"title": "X", "hook": "weird"}]}')
        self.assertEqual(points[0].hook, "none")

    def test_falls_back_to_lines_when_not_json(self):
        points = parse_tree("1. 第一点\n2. 第二点\n- 第三点")
        self.assertEqual([p.title for p in points], ["第一点", "第二点", "第三点"])


class ClassifyTeachingInputTests(unittest.TestCase):
    def test_stop_words(self):
        self.assertEqual(classify_teaching_input("退出"), "stop")
        self.assertEqual(classify_teaching_input("先这样吧"), "stop")

    def test_reteach_words(self):
        self.assertEqual(classify_teaching_input("这个没懂，再讲一遍"), "reteach")
        self.assertEqual(classify_teaching_input("换个讲法"), "reteach")

    def test_default_is_advance(self):
        self.assertEqual(classify_teaching_input("懂了，继续"), "advance")
        self.assertEqual(classify_teaching_input("我觉得是因为努力影响绩效"), "advance")


class SessionPersistenceTests(unittest.TestCase):
    def test_save_load_roundtrip_and_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = CramWorkspace.open(Path(tmp) / "通信原理")
            self.assertFalse(has_active_session(workspace))

            session = TeachingSession(
                topic="采样定理",
                points=[KnowledgePoint("采样", "none"), KnowledgePoint("混叠", "contrast")],
                current=1,
                started=True,
            )
            save_session(workspace, session)
            self.assertTrue(has_active_session(workspace))

            loaded = load_session(workspace)
            self.assertEqual(loaded.topic, "采样定理")
            self.assertEqual(loaded.current, 1)
            self.assertTrue(loaded.started)
            self.assertEqual([p.title for p in loaded.points], ["采样", "混叠"])

            clear_session(workspace)
            self.assertFalse(has_active_session(workspace))

    def test_finished_and_current_point(self):
        session = TeachingSession(topic="X", points=[KnowledgePoint("A")], current=0)
        self.assertFalse(session.finished)
        self.assertEqual(session.current_point().title, "A")
        session.current = 1
        self.assertTrue(session.finished)
        self.assertIsNone(session.current_point())


class RenderTreeTests(unittest.TestCase):
    def test_render_lists_topic_points_and_controls(self):
        session = TeachingSession(topic="期望理论", points=[KnowledgePoint("核心公式", "acronym"), KnowledgePoint("三变量")])
        rendered = render_tree(session)
        self.assertIn("期望理论", rendered)
        self.assertIn("1. 核心公式", rendered)
        self.assertIn("2. 三变量", rendered)
        self.assertIn("开始", rendered)


if __name__ == "__main__":
    unittest.main()
