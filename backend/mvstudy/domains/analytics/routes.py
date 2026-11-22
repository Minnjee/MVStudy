"""E2/E3 的 HTTP 面：班级统计与教师周报（8 号）。

身份来源优先取 flask.g.current_actor（正式 host 由 01 号在登录中间件注入，
结构同 U2 /me）；本地联调与 demo 退化为读取 X-Actor 请求头里的 JSON，
因此 01 号接入 JWT 后本文件无需修改。当前数据来自假快照，
接真表时只替换 fake_snapshot.load_snapshot。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import Blueprint, Flask, g, jsonify, request

from .fake_snapshot import load_snapshot
from .metrics import build_analytics, build_weekly_report

analytics_api = Blueprint("analytics", __name__, url_prefix="/api")

_TEACHER_RELATIONS = {"teacher", "head_teacher", "assistant", "ta", "owner", "manager"}


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def _actor() -> dict[str, Any] | None:
    """当前登录者：正式 host 注入优先，demo 从请求头模拟。"""
    actor = getattr(g, "current_actor", None)
    if isinstance(actor, dict):
        return actor
    raw = request.headers.get("X-Actor")
    if raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None
    return None


def _authorize(class_id: str):
    """返回 (actor, None) 或 (None, error_response)。跨班按 not_found 处理。"""
    actor = _actor()
    if not actor or not actor.get("user_id"):
        return None, _error("unauthenticated", "请先登录。", 401)
    role = actor.get("role_id")
    if role == "student":
        return None, _error("forbidden", "学生无权查看班级学情。", 403)
    if role == "admin":
        if "analytics.read" not in (actor.get("permissions") or []):
            return None, _error("forbidden", "管理员缺少学情读取权限。", 403)
        return actor, None
    if role == "teacher":
        classes = actor.get("classes") or []
        if any(c.get("class_id") == class_id and c.get("relation") in _TEACHER_RELATIONS
               for c in classes if isinstance(c, dict)):
            return actor, None
        return None, _error("not_found", "班级不存在或不在可读范围。", 404)
    return None, _error("forbidden", "当前角色无权查看班级学情。", 403)


def _parse_range(source: Any):
    """校验 from/to：必填、带时区、from < to。返回 (start, end, from_str, to_str)。"""
    frm, to = source.get("from"), source.get("to")
    if not isinstance(frm, str) or not isinstance(to, str):
        return None
    try:
        start = datetime.fromisoformat(frm.replace("Z", "+00:00"))
        end = datetime.fromisoformat(to.replace("Z", "+00:00"))
    except ValueError:
        return None
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        return None
    return start, end, frm, to


def _metrics_for(class_id: str, start: datetime, end: datetime) -> dict[str, Any] | None:
    snap = load_snapshot(class_id)
    if snap is None:
        return None
    return build_analytics(
        class_id=class_id,
        recipients=snap["recipients"],
        submissions=snap["submissions"],
        runs=snap["runs"],
        events=snap["events"],
        grades=snap["grades"],
        start=start,
        end=end,
        as_of=snap["as_of"],
    )


@analytics_api.get("/classes/<class_id>/analytics")
def class_analytics(class_id: str):
    """E2：授权教师/管理员读取班级统计。"""
    _actor_obj, err = _authorize(class_id)
    if err:
        return err
    parsed = _parse_range(request.args)
    if parsed is None:
        return _error("invalid_range", "from/to 必填、需带时区且 from 早于 to。", 400)
    start, end, _frm, _to = parsed
    metrics = _metrics_for(class_id, start, end)
    if metrics is None:
        return _error("not_found", "班级不存在。", 404)
    return jsonify(metrics)


@analytics_api.post("/classes/<class_id>/weekly-report")
def weekly_report(class_id: str):
    """E3：按同一统计快照生成教师周报。"""
    _actor_obj, err = _authorize(class_id)
    if err:
        return err
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error("invalid_range", "请求内容必须是 JSON 对象。", 400)
    parsed = _parse_range(body)
    if parsed is None:
        return _error("invalid_range", "from/to 必填、需带时区且 from 早于 to。", 400)
    start, end, frm, to = parsed
    metrics = _metrics_for(class_id, start, end)
    if metrics is None:
        return _error("not_found", "班级不存在。", 404)
    report = build_weekly_report(metrics)
    report["from"] = frm
    report["to"] = to
    return jsonify(report)


def create_analytics_demo() -> Flask:
    """仅供本地联调的最小宿主；正式 host 注册 analytics_api 即可。"""
    app = Flask(__name__)
    app.register_blueprint(analytics_api)
    return app
