"""种子数据（幂等：已存在则跳过）。

v0.2 内容：
1. 榜单：「cs榜」空榜（不预置人物 —— 榜单成员由管理员在管理台自行添加/批量导入）
2. 管理员账号：admin / admin123456（可用环境变量覆盖，见 config.DEFAULT_ADMIN）
3. 视频素材：迁移 yt.mp4 / 闫涛10.mp4 到 data/media（左右轮流播放用）
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from sqlalchemy import select

from .config import BASE_DIR, BOARD_NAME, DEFAULT_ADMIN, MEDIA_DIR
from .database import SessionLocal
from .models import Admin, Board
from .security import hash_password

_VIDEOS = ["yt.mp4", "闫涛10.mp4"]

# 视频素材来源候选（按顺序查找，找到即复制到 data/media/）：
# 1) exe / 项目同级的 video/ 目录（打包分发时最方便）
# 2) 原版程序发布目录里的 video/
_SOURCE_DIR_CANDIDATES = [
    BASE_DIR / "video",
    BASE_DIR.parent / "video",
    BASE_DIR / "好人榜1.2正式版（官方）(1)" / "video",
    Path(__file__).resolve().parent.parent.parent / "好人榜1.2正式版（官方）(1)" / "video",
]


def run_seed() -> None:
    db = SessionLocal()
    try:
        _seed_admin(db)
        _seed_boards(db)
        _seed_videos()
    finally:
        db.close()


def _seed_admin(db) -> None:
    if db.scalar(select(Admin).limit(1)) is not None:
        return
    db.add(Admin(username=DEFAULT_ADMIN["username"],
                 password_hash=hash_password(DEFAULT_ADMIN["password"])))
    db.commit()


def _seed_boards(db) -> None:
    if db.scalar(select(Board).limit(1)) is not None:
        return

    honor = Board(
        name=BOARD_NAME,
        slug="honor",
        tagline="年度人物排行榜 · 继承版",
        description="继承原版程序灵感的年度感谢榜：把最值得感谢的人，挂上最高的榜。"
                    "左右两边是献唱歌声，榜单横贯中央。",
        sort_order=0,
    )
    db.add(honor)
    db.commit()


def _run_migration(source: Path) -> int:
    """把 source 目录下的视频复制到 data/media/（已存在则跳过），返回复制数量。"""
    copied = 0
    try:
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    # 目录内所有 mp4 都收（不限于预置文件名，用户自己丢进去的也认）
    candidates = list(_VIDEOS)
    try:
        for extra in source.glob("*.mp4"):
            if extra.name not in candidates:
                candidates.append(extra.name)
    except OSError:
        pass
    for name in candidates:
        src = source / name
        dst = MEDIA_DIR / name
        try:
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                copied += 1
        except OSError:
            continue
    return copied


def _seed_videos() -> None:
    """视频素材迁移（按优先级）：内置素材 → exe/项目同级 video/ → 原版发布目录。

    内置素材（打包时随 exe 携带，位于 sys._MEIPASS/bundled_video）保证
    「一键部署」开箱即有歌声；外部目录可覆盖/补充。全部失败也不影响运行。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    candidates: list[Path] = []
    if meipass:
        candidates.append(Path(meipass) / "bundled_video")
    candidates.extend(_SOURCE_DIR_CANDIDATES)

    for source in candidates:
        try:
            if not source.exists():
                continue
        except OSError:
            continue
        if _run_migration(source) > 0:
            return
        # 该来源没有可复制的内容（或已全部存在）→ 继续尝试下一个来源
