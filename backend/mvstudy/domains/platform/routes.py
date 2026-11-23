"""U1/U2/U5 的 HTTP 面。

路由只做三件事：解析入参、取当前身份、调用用例并映射响应。
事务与授权判断都在 identity.py / classes.py 里，worker 与其他域复用同一份实现。

当前身份由宿主在 before_request 注入 g.current_actor，结构同 U2 响应。
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request

from .classes import list_members
from .identity import AuthError, login as login_use_case

platform_api = Blueprint("platform", __name__, url_prefix="/api")


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def _session():
    return current_app.extensions["session_factory"]()


def _actor() -> dict | None:
    actor = getattr(g, "current_actor", None)
    return actor if isinstance(actor, dict) and actor else None


@platform_api.post("/login")
def login_view():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error("invalid_json", "请求内容必须是 JSON 对象。", 400)
    login_name = body.get("login")
    password = body.get("password")
    if not isinstance(login_name, str) or not isinstance(password, str) or not login_name or not password:
        return _error("invalid_credentials", "登录名或密码不正确。", 401)
    session = _session()
    try:
        token = login_use_case(
            session,
            login_name,
            password,
            current_app.config["JWT_SECRET"],
            current_app.config["JWT_TTL_MINUTES"],
        )
    except AuthError as error:
        return _error(error.code, error.message, error.status)
    finally:
        session.close()
    return jsonify({"access_token": token}), 200


@platform_api.get("/me")
def me_view():
    actor = _actor()
    if actor is None:
        return _error("unauthenticated", "请先登录。", 401)
    return jsonify(actor)


@platform_api.get("/classes/<class_id>/members")
def members_view(class_id: str):
    actor = _actor()
    if actor is None:
        return _error("unauthenticated", "请先登录。", 401)
    session = _session()
    try:
        items = list_members(session, actor, class_id, request.args.get("relation"))
    finally:
        session.close()
    if items is None:
        return _error("not_found", "班级不存在或不在可读范围。", 404)
    return jsonify({"items": items})
