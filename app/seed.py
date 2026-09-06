"""种子数据（幂等：已存在则跳过）。

v0.1 内容：
1. 榜单：好人榜（继承 exe 灵感）+ 曝光榜（点进去看原因）
2. 好人榜 7 人（原版程序数据迁移，围观指数 = 原分数，保留“大数”梗）
3. 曝光榜 2 条示例事件（无实名特征描述，演示“上榜原因 + 处理结果”）
4. 管理员账号：admin / admin123456（可用环境变量覆盖，见 config.DEFAULT_ADMIN）
5. 视频素材：从发布目录迁移 yt.mp4 / 闫涛10.mp4 到 data/media（存在才复制）
"""
from __future__ import annotations

import json
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
                    "围观指数继承原版“大数级”分数，人越多，指数越高。",
        sort_order=0,
    )
    exposed = Board(
        name="曝光榜",
        slug="exposed",
        tagline="校园文明反馈 · 点进去，看原因",
        description="匿名反映校园里需要被看见的事（文明乱象、违规行为、需要处理的问题）。"
                    "评委规则：只描述行为、不公开实名。先审后上，留痕可查。",
        sort_order=1,
    )
    db.add_all([honor, exposed])
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

    # 示例事件（无实名，演示“上榜原因 + 处理结果”闭环）
    db.add(Report(
        board_id=exposed.id,
        title="教学楼三层男厕的‘艺术’涂鸦",
        who="某同学（特征：身高约一米七，常戴黑色帽子）",
        reason="连续三周周末，教学楼三层男厕隔板上出现大量记号笔涂鸦，含辱骂字句与表情符号，"
               "保洁阿姨每日清理后次日重现。已影响到正常的如厕环境，特此反映。",
        location="教学楼 3 层男厕",
        happened_at="2025 年 9 月起，每周六晚",
        heat=328,
        status=Report.STATUS_PROCESSED,
        process_result="已由总务处完成清理，并通过年级通报全校寻找线索、提醒文明使用公共设施。",
    ))
    db.add(Report(
        board_id=exposed.id,
        title="晚自习结束后的球场灯光骚扰",
        who="匿名（多名同学联名反映）",
        reason="晚自习结束后 21:30-22:30 期间，篮球场被个别同学持续占用并大声喊叫，"
               "影响附近宿舍楼内同学休息，多次劝阻无效，希望学校出面管理。",
        location="东区篮球场 / 毗邻的 2 号宿舍楼",
        happened_at="2025 年 10 月，每个工作日夜间",
        heat=512,
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
