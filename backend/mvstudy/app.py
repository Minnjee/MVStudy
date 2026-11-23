"""平台宿主：正式应用工厂与 7 号评审演示工厂。

正式工厂只做装配：注册 Blueprint、建立会话工厂、在每个请求注入 g.current_actor。
HTTP 路由一律放在负责该契约的业务域；本文件出现路由会被 tools/check_layout.py 拦下。
"""

from __future__ import annotations

import os

from flask import Flask, g, request
from flask_cors import CORS

from .config import load_config
from .db import build_engine, build_session_factory
from .domains.platform import load_current_actor
from .domains.platform.routes import platform_api
from .domains.platform.security import read_token
from .domains.review.routes import review_api

BEARER_PREFIX = "Bearer "


def create_app(config: dict | None = None) -> Flask:
    """正式平台入口；测试通过 config 覆盖 DATABASE_URL 指向隔离库。"""
    app = Flask(__name__)
    app.config.update(load_config())
    app.config.update(config or {})
    CORS(app, resources={r"/api/*": {"origins": app.config["WEB_ORIGIN"]}})

    app.extensions["engine"] = build_engine(app.config["DATABASE_URL"])
    app.extensions["session_factory"] = build_session_factory(app.extensions["engine"])

    @app.before_request
    def inject_current_actor() -> None:
        g.current_actor = None
        header = request.headers.get("Authorization", "")
        if not header.startswith(BEARER_PREFIX):
            return
        user_id = read_token(header[len(BEARER_PREFIX) :].strip(), app.config["JWT_SECRET"])
        if user_id is None:
            return
        session = app.extensions["session_factory"]()
        try:
            g.current_actor = load_current_actor(session, user_id)
        finally:
            session.close()

    app.register_blueprint(platform_api)
    return app


def create_review_demo() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024
    CORS(app, resources={r"/api/*": {"origins": os.getenv("WEB_ORIGIN", "http://localhost:5173")}})
    app.extensions["review_demo_records"] = {}
    app.register_blueprint(review_api)
    return app
