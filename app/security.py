"""安全工具：密码哈希 + 登录态校验。

v0.1 采用标准库 sha256 + 随机盐 + HMAC 迭代（无第三方依赖）。
迭代次数等参数可在 v0.2 升级为 bcrypt/argon2 时平滑替换。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import Admin

_ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
    """返回 salt$hash 格式（hex）。"""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    actual = hash_password(password, salt=salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def current_admin(request: Request, db: Annotated[Session, Depends(get_db)]) -> Admin | None:
    """会话中的管理员；未登录返回 None。"""
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    return db.get(Admin, int(admin_id)) if isinstance(admin_id, int) else None


def admin_required(admin: Annotated[Admin | None, Depends(current_admin)]) -> Admin | None:
    """路由守卫（FastAPI 依赖注入）：未登录重定向到登录页无法直接在此表达，
    因此由各路由显式检查；本依赖用于统一类型标注。"""
    return admin
