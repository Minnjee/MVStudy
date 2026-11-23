"""Alembic 运行环境。

连接串统一从环境变量 / .env 读取，不写死在 alembic.ini。
新增业务域时把它的模型模块 import 进来，即可进入同一个 Base.metadata。
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from mvstudy.config import load_config
from mvstudy.db import Base
from mvstudy.domains.platform import models as platform_models  # noqa: F401  注册表结构

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def resolved_url() -> str:
    return os.getenv("DATABASE_URL") or load_config()["DATABASE_URL"]


def run_migrations_offline() -> None:
    context.configure(
        url=resolved_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = resolved_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
