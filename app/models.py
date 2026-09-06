"""ORM 数据模型。

v0.1 模型说明（后续迭代保持不变，仅扩展字段）：
- Board   榜单（如「好人榜」「曝光榜」），一榜一故事
- Report  上榜条目：
    * 好人榜语境 = 人物事迹（title 为题头、reason 为事迹/上榜理由）
    * 曝光榜语境 = 事件反映（title 为事件标题、reason 为事件经过/上榜原因）
  who 字段一律只存「特征描述」（班级/昵称/外形特征），禁止存身份证号、
  照片、手机号等可直接识别本人的实名信息 —— 这是合规红线。
- Admin   管理员账号（密码以加盐哈希存储）
- Log     管理员操作日志（留痕：谁在何时对什么做了什么）
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tagline: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reports: Mapped[list["Report"]] = relationship(back_populates="board")


class Report(Base):
    __tablename__ = "reports"

    STATUS_PENDING = "pending"      # 待审核
    STATUS_APPROVED = "approved"    # 已公示（上榜）
    STATUS_REJECTED = "rejected"    # 已驳回
    STATUS_TRANSFERRED = "transferred"  # 已转交学校相关部门
    STATUS_PROCESSED = "processed"  # 已处理（有处理结果）

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))          # 标题（梗句/事件名）
    who: Mapped[str] = mapped_column(String(80), default="匿名")  # 对象特征描述（无实名）
    reason: Mapped[str] = mapped_column(Text)                # 上榜原因 / 事件经过
    location: Mapped[str] = mapped_column(String(120), default="")  # 地点
    happened_at: Mapped[str] = mapped_column(String(40), default="")  # 时间描述（自由文本）
    heat: Mapped[int] = mapped_column(BigInteger, default=0)  # 围观指数（继承“大数级”梗）
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    reject_reason: Mapped[str] = mapped_column(Text, default="")
    process_result: Mapped[str] = mapped_column(Text, default="")   # 处理结果（曝光榜）
    evidence: Mapped[str] = mapped_column(Text, default="[]")       # 证据文件 JSON 列表（v0.2 上传）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    board: Mapped[Board] = relationship(back_populates="reports")

    @property
    def status_label(self) -> str:
        return {
            "pending": "待审核",
            "approved": "已公示",
            "rejected": "已驳回",
            "transferred": "已转交",
            "processed": "已处理",
        }.get(self.status, self.status)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True)
    admin_name: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(64))      # approve / reject / transfer / process / login ...
    target_type: Mapped[str] = mapped_column(String(40), default="")
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
