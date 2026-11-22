"""工单 15：E1 幂等接收班级学习事件。

设计要点（对照 interfaces.md E1 与 task-08-spec）：
- 用生产方生成的 event_id 去重：同编号同内容重放只写一次（inserted=False）。
- 同编号异内容报 event_conflict，不覆盖原记录。
- 只保留可归属用户和课堂的最少元信息；不存原图、学生代码、提示词。
- 类型按 E1 白名单校验，必填字段缺失报 invalid_event。
- store 是一个 dict（生产环境替换为仓储），事件以规范化载荷存储。
"""
from __future__ import annotations

from typing import Any

# E1 允许的事件类型（interfaces.md 单一生产方清单）
ALLOWED_TYPES = {
    "run.finished",
    "assignment.published",
    "grade.saved",
    "question.answered",
    "tool.finished",
    "submission.created",
}

# 必填字段
REQUIRED = {"event_id", "type", "occurred_at", "user_id", "status"}

# 合法的显式字段白名单（其余一律不入库，天然屏蔽敏感字段）
ALLOWED_FIELDS = {
    "event_id", "type", "occurred_at", "user_id", "status",
    "class_id", "assignment_id", "submission_id", "run_id",
    "topic", "source", "tool",
}


class InvalidEvent(ValueError):
    """事件不符合 E1 契约（缺字段、类型非法）。"""


class EventConflict(ValueError):
    """同一 event_id 对应了不同内容。"""


def _normalize(event: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化事件：补齐空 class_id，剔除白名单外字段。"""
    missing = REQUIRED - event.keys()
    if missing:
        raise InvalidEvent(f"缺少必填字段: {sorted(missing)}")
    if event["type"] not in ALLOWED_TYPES:
        raise InvalidEvent(f"非法事件类型: {event['type']!r}")

    clean = {k: v for k, v in event.items() if k in ALLOWED_FIELDS}
    clean.setdefault("class_id", "")
    return clean


def record_event(event: dict[str, Any], store: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """把一条 E1 事件写入 store，保证幂等。

    返回 {"event_id": str, "inserted": bool}。
    - 同编号同内容重放 -> inserted=False，不重复写。
    - 同编号异内容 -> 抛 EventConflict。
    """
    clean = _normalize(event)
    event_id = clean["event_id"]

    if event_id in store:
        if store[event_id] == clean:
            return {"event_id": event_id, "inserted": False}
        raise EventConflict(f"event_id {event_id!r} 已存在不同内容")

    store[event_id] = clean
    return {"event_id": event_id, "inserted": True}
