"""U5 用例：读取班级名册。

授权只有两条路径：管理员持管理权限，或教师是该班成员。
其余一律按 not_found 处理，不向调用方泄露班级是否存在。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ClassMember, User

MANAGE_PERMISSION = "admin.users"
TEACHER_RELATIONS = {"teacher"}


def _can_read(session: Session, actor: dict[str, Any], class_id: str) -> bool:
    if actor.get("role_id") == "admin" and MANAGE_PERMISSION in (actor.get("permissions") or []):
        return True
    if actor.get("role_id") != "teacher":
        return False
    return session.scalar(
        select(ClassMember.user_id).where(
            ClassMember.class_id == class_id,
            ClassMember.user_id == actor["user_id"],
            ClassMember.relation == "teacher",
        )
    ) is not None


def list_members(
    session: Session, actor: dict[str, Any], class_id: str, relation: str | None = None
) -> list[dict[str, Any]] | None:
    """返回名册条目；无权读取时返回 None，由路由映射为 404。"""
    if not _can_read(session, actor, class_id):
        return None
    statement = (
        select(User.user_id, User.display_name, ClassMember.relation)
        .join(ClassMember, ClassMember.user_id == User.user_id)
        .where(ClassMember.class_id == class_id)
        .order_by(ClassMember.relation, User.user_id)
    )
    if relation:
        statement = statement.where(ClassMember.relation == relation)
    return [
        {"user_id": user_id, "display_name": display_name, "relation": row_relation}
        for user_id, display_name, row_relation in session.execute(statement).all()
    ]
