"""01 域身份与班级模型。字段、约束以 docs/database.md 为准。

四张表由本域独占写入：roles、users、classes、class_members。
"""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from mvstudy.db import Base

RELATIONS = ("teacher", "student")


class Role(Base):
    """角色键与功能权限码；班级范围另行由 class_members 决定。"""

    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )


class User(Base):
    """登录账号。密码只存摘要，接口不回传本表任何敏感字段。"""

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    login: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.role_id", name="fk_users_role"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class SchoolClass(Base):
    """班级。名册用预置数据导入，不做教务排课。"""

    __tablename__ = "classes"

    class_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)


class ClassMember(Base):
    """班内关系，是各项班级范围授权的唯一来源。"""

    __tablename__ = "class_members"
    __table_args__ = (
        CheckConstraint("relation IN ('teacher', 'student')", name="ck_class_members_relation"),
        Index("ix_class_members_user_id", "user_id"),
    )

    class_id: Mapped[str] = mapped_column(
        ForeignKey("classes.class_id", name="fk_class_members_class"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", name="fk_class_members_user"), primary_key=True
    )
    relation: Mapped[str] = mapped_column(Text, nullable=False)
