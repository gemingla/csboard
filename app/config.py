"""应用配置：路径、数据库、安全密钥、品牌信息。

- BASE_DIR  : 项目根目录（源码运行时）/ exe 所在目录（PyInstaller 打包运行时）
- DATA_DIR  : 运行时数据（SQLite 数据库、上传素材），已加入 .gitignore
- 安全密钥  : 首次启动自动生成到 data/secret.key，可用于重启后保持会话/签名稳定

注意：onefile 打包后 __file__ 指向临时解包目录（每次启动都会被清理），
因此数据目录必须锚定到 exe 同级目录，否则数据会在退出后丢失。
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    # exe 所在目录（数据、素材、备份都放这里，绿色免安装）
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "beastboard.db"
SECRET_KEY_FILE = DATA_DIR / "secret.key"

# ---- 品牌 ----
APP_NAME = "cs榜"
APP_SLUG = "csboard"
BOARD_NAME = "cs榜"          # 榜单显示名（迁移时同步到已存在的榜单记录）
VERSION = "0.2.7"
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
