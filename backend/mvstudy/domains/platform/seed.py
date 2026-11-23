"""幂等的开发种子：两个班、三类角色、十个账号。

用法（在 backend/ 目录下）：
    python -m mvstudy.domains.platform.seed

重复执行不会产生重复数据。生产环境不使用本入口。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from mvstudy.db import build_engine, build_session_factory

from .models import ClassMember, Role, SchoolClass, User
from .security import hash_password

ROLES = (
    ("student", "学生", ["case.read", "submission.write"]),
    ("teacher", "教师", ["case.read", "grade.write", "analytics.read"]),
    (
        "admin",
        "管理员",
        [
            "admin.users",
            "admin.roles",
            "case.read",
            "case.write",
            "run.create",
            "grade.write",
            "analytics.read",
        ],
    ),
)

CLASSES = (("c1", "机器视觉 2026 春 1 班"), ("c2", "机器视觉 2026 春 2 班"))

ACCOUNTS = (
    ("u-a01", "a01", "平台管理员", "admin", "Admin@123"),
    ("u-t01", "t01", "王老师", "teacher", "Teach@123"),
    ("u-t02", "t02", "李老师", "teacher", "Teach@123"),
    ("u-s01", "s01", "李同学", "student", "Stud@123"),
    ("u-s02", "s02", "张同学", "student", "Stud@123"),
    ("u-s03", "s03", "陈同学", "student", "Stud@123"),
    ("u-s04", "s04", "赵同学", "student", "Stud@123"),
    ("u-s05", "s05", "周同学", "student", "Stud@123"),
    ("u-s06", "s06", "吴同学", "student", "Stud@123"),
    ("u-s07", "s07", "徐同学", "student", "Stud@123"),
    ("u-s08", "s08", "孙同学", "student", "Stud@123"),
)

MEMBERSHIPS = (
    ("c1", "u-t01", "teacher"),
    ("c2", "u-t02", "teacher"),
    ("c1", "u-s01", "student"),
    ("c1", "u-s02", "student"),
    ("c1", "u-s03", "student"),
    ("c1", "u-s04", "student"),
    ("c2", "u-s05", "student"),
    ("c2", "u-s06", "student"),
    ("c2", "u-s07", "student"),
    ("c2", "u-s08", "student"),
)


def seed(session: Session) -> dict[str, int]:
    """按固定键补齐缺失行；已存在的一律跳过。"""
    created = {"roles": 0, "classes": 0, "users": 0, "members": 0}

    for role_id, name, permissions in ROLES:
        if session.get(Role, role_id) is None:
            session.add(Role(role_id=role_id, name=name, permissions=list(permissions)))
            created["roles"] += 1

    for class_id, name in CLASSES:
        if session.get(SchoolClass, class_id) is None:
            session.add(SchoolClass(class_id=class_id, name=name))
            created["classes"] += 1

    session.flush()

    for user_id, login_name, display_name, role_id, password in ACCOUNTS:
        if session.scalar(select(User.user_id).where(User.login == login_name)) is None:
            session.add(
                User(
                    user_id=user_id,
                    login=login_name,
                    display_name=display_name,
                    password_hash=hash_password(password),
                    role_id=role_id,
                )
            )
            created["users"] += 1

    session.flush()

    for class_id, user_id, relation in MEMBERSHIPS:
        exists = session.scalar(
            select(ClassMember.user_id).where(
                ClassMember.class_id == class_id, ClassMember.user_id == user_id
            )
        )
        if exists is None:
            session.add(ClassMember(class_id=class_id, user_id=user_id, relation=relation))
            created["members"] += 1

    session.commit()
    return created


def main() -> None:
    session = build_session_factory(build_engine())()
    try:
        created = seed(session)
    finally:
        session.close()
    summary = "，".join(f"{key} 新增 {value}" for key, value in created.items())
    if any(created.values()):
        print(f"种子完成：{summary}")
    else:
        print("种子已存在，无需变更。")


if __name__ == "__main__":
    main()
