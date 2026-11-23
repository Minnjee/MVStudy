"""平台共用的 Declarative Base 与数据库会话。

全部业务模型注册到同一个 Base.metadata；建表和升级只走 Alembic，
应用启动与测试都不调用 create_all()。
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """九个业务域共用的模型基类。"""


def build_engine(url: str | None = None) -> Engine:
    from .config import database_url

    return create_engine(url or database_url(), pool_pre_ping=True, future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
