"""联调假数据：真实事件表就绪前，为 E2/E3 提供固定的班级快照。

将来接真表（26 号后半段）时，只需替换 load_snapshot 的实现，
路由与统计口径都不用改。c1 刻意覆盖工单 08 的验收场景：
4 个应交名额、2 人提交、其中 1 人重交 -> 完成率 0.5。
"""
from __future__ import annotations

from typing import Any

AS_OF = "2026-11-21T10:00:00+08:00"

_SNAPSHOTS: dict[str, dict[str, Any]] = {
    "c1": {
        "as_of": AS_OF,
        "recipients": [
            {"student_id": u, "assignment_id": "a1", "published_at": "2026-11-16T09:00:00+08:00"}
            for u in ("u1", "u2", "u3", "u4")
        ],
        "submissions": [
            {"submission_id": "s1", "student_id": "u1", "assignment_id": "a1",
             "revision": 1, "submitted_at": "2026-11-18T10:00:00+08:00"},
            {"submission_id": "s2", "student_id": "u1", "assignment_id": "a1",
             "revision": 2, "submitted_at": "2026-11-19T10:00:00+08:00"},
            {"submission_id": "s3", "student_id": "u2", "assignment_id": "a1",
             "revision": 1, "submitted_at": "2026-11-20T10:00:00+08:00"},
        ],
        "runs": [
            {"status": "succeeded"}, {"status": "succeeded"},
            {"status": "failed"}, {"status": "queued"},
        ],
        "events": [
            {"type": "question.answered", "topic": "阈值"},
            {"type": "question.answered", "topic": "阈值"},
            {"type": "question.answered", "topic": "边缘检测"},
            {"type": "tool.finished", "topic": "阈值"},
        ],
        "grades": [
            {"submission_id": "s2", "score": 95},
            {"submission_id": "s3", "score": 75},
        ],
    },
    "c2": {
        "as_of": AS_OF,
        "recipients": [
            {"student_id": u, "assignment_id": "a2", "published_at": "2026-11-16T09:00:00+08:00"}
            for u in ("v1", "v2", "v3")
        ],
        "submissions": [
            {"submission_id": "t1", "student_id": "v1", "assignment_id": "a2",
             "revision": 1, "submitted_at": "2026-11-18T09:00:00+08:00"},
        ],
        "runs": [],
        "events": [],
        "grades": [],
    },
    "c3": {
        "as_of": AS_OF,
        "recipients": [],
        "submissions": [],
        "runs": [],
        "events": [],
        "grades": [],
    },
}


def load_snapshot(class_id: str) -> dict[str, Any] | None:
    """返回班级快照；未知班级返回 None（路由据此回 404）。"""
    snap = _SNAPSHOTS.get(class_id)
    if snap is None:
        return None
    return {
        "as_of": snap["as_of"],
        "recipients": list(snap["recipients"]),
        "submissions": list(snap["submissions"]),
        "runs": list(snap["runs"]),
        "events": list(snap["events"]),
        "grades": list(snap["grades"]),
    }
