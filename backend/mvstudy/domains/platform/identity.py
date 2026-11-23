"""U1/U2 用例：登录与读取当前身份。

JWT 只标识 user_id；enabled、角色权限与班级关系每次请求重新查库，
因此停用账号或撤销权限后下一个请求立即生效。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ClassMember, Role, User
from .security import issue_token, verify_password


class AuthError(Exception):
    """登录失败。对外只暴露 invalid_credentials，避免账号可枚举。"""

    def __init__(self, message: str = "登录名或密码不正确。") -> None:
        super().__init__(message)
        self.code = "invalid_credentials"
        self.message = message
        self.status = 401


def login(session: Session, login_name: str, password: str, secret: str, ttl_minutes: int) -> str:
    """校验口令并签发凭证。账号不存在、已停用、口令错误返回同一错误。"""
    user = session.scalar(select(User).where(User.login == login_name))
    if user is None or not user.enabled or not verify_password(password, user.password_hash):
        raise AuthError()
    return issue_token(user.user_id, secret, ttl_minutes)


def load_current_actor(session: Session, user_id: str) -> dict[str, Any] | None:
    """组装 g.current_actor / U2 响应；结构供 4、8、9 号直接消费。"""
    user = session.get(User, user_id)
    if user is None or not user.enabled:
        return None
    role = session.get(Role, user.role_id)
    memberships = session.execute(
        select(ClassMember.class_id, ClassMember.relation)
        .where(ClassMember.user_id == user_id)
        .order_by(ClassMember.class_id)
    ).all()
    return {
        "user_id": user.user_id,
        "display_name": user.display_name,
        "role_id": user.role_id,
        "permissions": list(role.permissions) if role is not None else [],
        "classes": [
            {"class_id": class_id, "relation": relation} for class_id, relation in memberships
        ],
    }
