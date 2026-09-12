"""轻量数据库迁移（幂等）：SQLite 加列 + 品牌名同步。

在应用启动时执行，保证老数据无损升级：
1. reports.sort_order —— 手动排序用（v0.2 新增）；缺失则补列并按围观指数初始化
2. boards.name 同步为当前品牌名（cs榜）
"""
from __future__ import annotations

from sqlalchemy import select, text

from .config import BOARD_NAME
from .database import SessionLocal, engine
from .models import Board, Report


def run_migrations() -> None:
    _ensure_sort_order_column()
    _sync_board_brand()


def _ensure_sort_order_column() -> None:
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(reports)"))]
        if "sort_order" in cols:
            return
        conn.execute(text("ALTER TABLE reports ADD COLUMN sort_order INTEGER DEFAULT 0"))
        conn.commit()
        # 初始化：按围观指数降序编号（10, 20, 30 ...），保持原有名次观感
        rows = list(conn.execute(text("SELECT id FROM reports ORDER BY heat DESC")))
        for idx, (rid,) in enumerate(rows, start=1):
            conn.execute(text("UPDATE reports SET sort_order = :o WHERE id = :i"),
                         {"o": idx * 10, "i": rid})
        conn.commit()


def _sync_board_brand() -> None:
    db = SessionLocal()
    try:
        changed = False
        for board in db.scalars(select(Board)):
            if board.name != BOARD_NAME:
                board.name = BOARD_NAME
                changed = True
        # 历史条目自动标题前缀统一（「年度好人 · X」→「cs榜 · X」）
        for report in db.scalars(select(Report).where(Report.title.like("年度好人%"))):
            report.title = report.title.replace("年度好人", BOARD_NAME, 1)
            changed = True
        if changed:
            db.commit()
    finally:
        db.close()
