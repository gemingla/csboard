"""种子数据（幂等：已存在则跳过）。

v0.1.1 内容：
1. 榜单：仅「好人榜」（继承 exe 灵感；曝光榜与反馈功能已按要求移除）
2. 好人榜 7 人（原版程序数据迁移，围观指数 = 原分数，保留“大数”梗）
3. 管理员账号：admin / admin123456（可用环境变量覆盖，见 config.DEFAULT_ADMIN）
4. 视频素材：迁移 yt.mp4 / 闫涛10.mp4 到 data/media（左右轮流播放用）
"""
from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select

from .config import DEFAULT_ADMIN, MEDIA_DIR
from .database import SessionLocal
from .models import Admin, Board, Report
from .security import hash_password

_HONOR_DATA = [
    ("周稳", 999999999999999),
    ("叶佩剑", 999999999999998),
    ("章蕾", 111111111111119),
    ("周怡", 111111111),
    ("熊志远", 5000),
    ("赵志成", 3000),
    ("卞美玲", 300),
]

_VIDEOS = ["yt.mp4", "闫涛10.mp4"]

_SOURCE_DIR_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / "好人榜1.2正式版（官方）(1)" / "video",
    Path("好人榜1.2正式版（官方）(1)") / "video",
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
        name="好人榜",
        slug="honor",
        tagline="感动中国 2023-2024 年度人物排行榜 · 继承版",
        description="继承原版程序灵感的年度感谢榜：把最值得感谢的人，挂上最高的榜。"
                    "左右两边是献唱歌声，榜单横贯中央。",
        sort_order=0,
    )
    db.add(honor)
    db.commit()

    for name, heat in _HONOR_DATA:
        db.add(Report(
            board_id=honor.id,
            title=f"年度好人 · {name}",
            who=name,
            reason="原版《好人榜 1.2》年度上榜人物。"
                   "本条目为历史数据迁移，详细事迹与颁奖词将在 v0.3 揭榜仪式中展开。",
            happened_at="2023-2024 年度",
            heat=heat,
            status=Report.STATUS_APPROVED,
        ))
    db.commit()


def _seed_videos() -> None:
    """视频素材迁移：优先取发布目录，找不到则跳过（不影响运行）。"""
    source = None
    for cand in _SOURCE_DIR_CANDIDATES:
        try:
            if cand.exists():
                source = cand
                break
        except OSError:
            continue
    if source is None:
        return
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    for name in _VIDEOS:
        src = source / name
        if src.exists() and not (MEDIA_DIR / name).exists():
            try:
                shutil.copy2(src, MEDIA_DIR / name)
            except OSError:
                continue
