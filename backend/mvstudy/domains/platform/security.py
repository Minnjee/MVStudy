"""密码摘要与 JWT 签发。

JWT 只承载 user_id 与过期时间：角色、权限、enabled、班级关系一律逐次查库，
这样停用账号或撤销权限后下一个请求即生效。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

ALGORITHM = "HS256"


def hash_password(raw: str) -> str:
    return generate_password_hash(raw)


def verify_password(raw: str, stored: str) -> bool:
    return check_password_hash(stored, raw)


def issue_token(user_id: str, secret: str, ttl_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=ttl_minutes)}
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def read_token(token: str, secret: str) -> str | None:
    """返回 token 中的 user_id；签名错误、过期或结构不符一律返回 None。"""
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) and subject else None
