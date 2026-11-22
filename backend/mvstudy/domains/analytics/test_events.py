"""工单 15：E1 幂等接收班级学习事件的验收测试。

覆盖两条验收条件：
1. 同一 event_id、同内容重放只写一次；同编号异内容返回 event_conflict。
2. 个人学习保留空 class_id；不存原图/学生代码/提示词；类型及来源按 E1 校验。
"""
import unittest

from mvstudy.domains.analytics.events import (
    EventConflict,
    InvalidEvent,
    record_event,
)


def valid_event(**overrides):
    """构造一条合法 E1 事件，测试里按需覆盖字段。"""
    event = {
        "event_id": "e1",
        "type": "submission.created",
        "occurred_at": "2026-11-18T10:00:00+08:00",
        "user_id": "u1",
        "status": "submitted",
        "class_id": "c1",
        "assignment_id": "a1",
        "submission_id": "s1",
    }
    event.update(overrides)
    return event


class TestIdempotency(unittest.TestCase):
    def setUp(self):
        self.store = {}

    def test_same_event_replay_inserted_once(self):
        """同编号同内容重放：第一次 inserted=True，之后 False，且只存一条。"""
        first = record_event(valid_event(), self.store)
        second = record_event(valid_event(), self.store)
        self.assertTrue(first["inserted"])
        self.assertFalse(second["inserted"])
        self.assertEqual(first["event_id"], "e1")
        self.assertEqual(len(self.store), 1)

    def test_same_id_different_content_is_conflict(self):
        """同编号但内容不同（status 改了）必须报冲突，不覆盖原记录。"""
        record_event(valid_event(), self.store)
        with self.assertRaises(EventConflict):
            record_event(valid_event(status="failed"), self.store)
        self.assertEqual(len(self.store), 1)

    def test_replay_ignores_key_order(self):
        """字典键顺序不同不算内容不同，仍视为同一事件。"""
        record_event(valid_event(), self.store)
        reordered = dict(reversed(list(valid_event().items())))
        result = record_event(reordered, self.store)
        self.assertFalse(result["inserted"])


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.store = {}

    def test_missing_required_field_rejected(self):
        """缺少必填字段（如 status）返回 invalid_event。"""
        bad = valid_event()
        del bad["status"]
        with self.assertRaises(InvalidEvent):
            record_event(bad, self.store)

    def test_unknown_type_rejected(self):
        """类型不在 E1 白名单里必须拒绝。"""
        with self.assertRaises(InvalidEvent):
            record_event(valid_event(type="unknown.event"), self.store)

    def test_personal_learning_keeps_empty_class_id(self):
        """个人学习允许空 class_id，不当成错误。"""
        result = record_event(
            valid_event(type="tool.finished", class_id="", status="succeeded",
                        assignment_id=None, submission_id=None,
                        source="assistant", tool="analytics_query"),
            self.store,
        )
        self.assertTrue(result["inserted"])
        self.assertEqual(self.store["e1"]["class_id"], "")

    def test_sensitive_fields_not_stored(self):
        """原图、学生代码、提示词不得写入存储。"""
        event = valid_event(
            image="/path/to/original.png",
            student_code="print('secret')",
            prompt="完整提示词内容",
        )
        record_event(event, self.store)
        stored = self.store["e1"]
        self.assertNotIn("image", stored)
        self.assertNotIn("student_code", stored)
        self.assertNotIn("prompt", stored)


if __name__ == "__main__":
    unittest.main()
