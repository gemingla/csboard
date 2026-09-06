"""应用配置：路径、数据库、安全密钥。

- BASE_DIR  : 项目根目录（beastboard/）
- DATA_DIR  : 运行时数据（SQLite 数据库、上传素材），已加入 .gitignore
- 安全密钥  : 首次启动自动生成到 data/secret.key，可用于重启后保持会话/签名稳定
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "beastboard.db"
SECRET_KEY_FILE = DATA_DIR / "secret.key"

APP_NAME = "畜牲榜 · BeastBoard"
VERSION = "0.1.0"
MOTTO = "把最该感谢的人，挂上最高的榜。"

DEFAULT_ADMIN = {"username": os.environ.get("BB_ADMIN_USER", "admin"),
                 "password": os.environ.get("BB_ADMIN_PASSWORD", "admin123456")}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def load_secret_key() -> str:
    """读取或生成签名密钥（用于 fastapi SessionMiddleware）。"""
    ensure_dirs()
    if SECRET_KEY_FILE.exists():
        key = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    key = secrets.token_hex(32)
    SECRET_KEY_FILE.write_text(key, encoding="utf-8")
    return key
