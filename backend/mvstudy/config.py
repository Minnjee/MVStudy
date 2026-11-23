"""平台宿主配置：只从环境变量读取，应用工厂与 Alembic 共用同一份。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql+psycopg://mvstudy:mvstudy@127.0.0.1:5433/mvstudy"


def load_config() -> dict:
    """读取 .env 后返回 Flask 可直接 update 的配置字典。"""
    load_dotenv(ROOT / ".env")
    return {
        "DATABASE_URL": os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        "JWT_SECRET": os.getenv("JWT_SECRET", "local-dev-only"),
        "JWT_TTL_MINUTES": int(os.getenv("JWT_TTL_MINUTES", "480")),
        "FILE_STORAGE_DIR": str(Path(os.getenv("FILE_STORAGE_DIR", str(ROOT / "var" / "files"))).expanduser()),
        "MAX_CONTENT_LENGTH": int(os.getenv("MAX_CONTENT_LENGTH", str(512 * 1024))),
        "WEB_ORIGIN": os.getenv("WEB_ORIGIN", "http://localhost:5173"),
    }


def database_url() -> str:
    """迁移命令与测试夹具统一从这里取连接串。"""
    return load_config()["DATABASE_URL"]
