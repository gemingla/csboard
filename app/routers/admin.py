"""管理员路由：登录、工作台、审核队列、案件处理、操作日志。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Admin, Board, Log, Report
from ..security import current_admin, verify_password

router = APIRouter(prefix="/admin")


def _tpl(request: Request, name: str, **ctx):
    return request.app.state.templates.TemplateResponse(
        request=request, name=name,
        context={"app_name": request.app.state.app_name,
                 "motto": request.app.state.motto, **ctx},
    )


def _log(db: Session, admin: Admin | None, action: str, target: type | None = None,
         target_id: int | None = None, detail: str = "") -> None:
    """写入管理员操作日志（留痕）。"""
    db.add(Log(admin_id=admin.id if admin else None,
               admin_name=admin.username if admin else "系统",
               action=action,
               target_type=target.__name__ if target else "",
               target_id=target_id, detail=detail))


@router.get("/login")
def login_page(request: Request):
    return _tpl(request, "admin/login.html", error=None)


@router.post("/login")
def login(request: Request, db: Annotated[Session, Depends(get_db)],
          username: Annotated[str, Form()], password: Annotated[str, Form()]):
    admin = db.scalar(select(Admin).where(Admin.username == username))
    if admin and verify_password(password, admin.password_hash):
        request.session["admin_id"] = admin.id
        _log(db, admin, "login", detail="管理员登录")
        db.commit()
        return RedirectResponse("/admin/", status_code=303)
    return _tpl(request, "admin/login.html", error="用户名或密码错误")


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/")
def dashboard(request: Request, db: Annotated[Session, Depends(get_db)]):
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    stats = {
        "pending": db.scalar(select(func.count()).select_from(Report).where(Report.status == Report.STATUS_PENDING)) or 0,
        "approved": db.scalar(select(func.count()).select_from(Report).where(Report.status == Report.STATUS_APPROVED)) or 0,
        "processed": db.scalar(select(func.count()).select_from(Report).where(Report.status == Report.STATUS_PROCESSED)) or 0,
        "rejected": db.scalar(select(func.count()).select_from(Report).where(Report.status == Report.STATUS_REJECTED)) or 0,
        "transferred": db.scalar(select(func.count()).select_from(Report).where(Report.status == Report.STATUS_TRANSFERRED)) or 0,
        "heat": db.scalar(select(func.coalesce(func.sum(Report.heat), 0))) or 0,
    }
    pending = db.scalars(
        select(Report).where(Report.status == Report.STATUS_PENDING).order_by(Report.created_at.desc())
    ).all()
    recent = db.scalars(
        select(Report).order_by(Report.created_at.desc()).limit(12)
    ).all()
    return _tpl(request, "admin/dashboard.html", admin=admin, stats=stats,
                pending=pending, recent=recent, cur_page="dashboard")


@router.get("/reports")
def reports_page(request: Request, db: Annotated[Session, Depends(get_db)],
                 status: str = ""):
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    stmt = select(Report).order_by(Report.created_at.desc())
    if status:
        stmt = stmt.where(Report.status == status)
    reports = db.scalars(stmt).all()
    boards = db.scalars(select(Board).where(Board.is_active == True).order_by(Board.sort_order)).all()  # noqa: E712
    return _tpl(request, "admin/reports.html", admin=admin, reports=reports,
                cur=status, boards=boards, error=None, cur_page="reports")


@router.post("/reports/add-fast")
def add_fast(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    who: Annotated[str, Form()],
    reason: Annotated[str, Form()] = "",
    heat: Annotated[str, Form()] = "0",
):
    """快速添加：一行完成 —— 姓名(必填)+事迹(可选)+围观指数(可选)。
    标题自动生成为「年度好人 · 姓名」；返回后停留在后台并聚焦姓名框，支持连续录入。"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    board_obj = db.scalar(select(Board).order_by(Board.sort_order).limit(1))
    if board_obj is None:
        return RedirectResponse("/admin/reports", status_code=303)
    try:
        heat_val = max(0, int(heat or 0))
    except ValueError:
        heat_val = 0
    name = (who or "匿名").strip()[:60]
    report = Report(
        board_id=board_obj.id,
        title=f"年度好人 · {name}"[:120],
        who=name,
        reason=reason,
        heat=heat_val,
        status=Report.STATUS_APPROVED,
    )
    db.add(report)
    _log(db, admin, "add", target=Report, detail=f"快速添加: {name}")
    db.commit()
    return RedirectResponse("/admin/reports#add-fast", status_code=303)


@router.post("/reports/add")
def add_report(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    title: Annotated[str, Form()],
    who: Annotated[str, Form()] = "",
    reason: Annotated[str, Form()] = "",
    heat: Annotated[str, Form()] = "0",
    happened_at: Annotated[str, Form()] = "",
    location: Annotated[str, Form()] = "",
    board: Annotated[str, Form()] = "",
):
    """管理员直接添加榜单成员：填表即上墙（status=approved，无需审核）。"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    board_obj = db.scalar(select(Board).where(Board.slug == board)) if board else \
        db.scalar(select(Board).order_by(Board.sort_order).limit(1))
    if board_obj is None:
        return RedirectResponse("/admin/reports", status_code=303)
    try:
        heat_val = max(0, int(heat or 0))
    except ValueError:
        heat_val = 0
    report = Report(
        board_id=board_obj.id,
        title=(title or "未命名人物")[:120],
        who=(who or "匿名")[:80],
        reason=reason,
        heat=heat_val,
        happened_at=happened_at[:40],
        location=location[:120],
        status=Report.STATUS_APPROVED,
    )
    db.add(report)
    _log(db, admin, "add", target=Report, detail=f"添加榜单成员: {report.title}")
    db.commit()
    db.refresh(report)
    # 停留在管理后台（榜单管理页），便于管理员连续添加
    return RedirectResponse("/admin/reports", status_code=303)


@router.post("/report/{report_id}/delete")
def delete_report(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    """删除榜单条目（留痕）。"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    report = db.get(Report, report_id)
    if report is not None:
        _log(db, admin, "delete", target=Report, target_id=report_id,
             detail=f"删除条目: {report.title}")
        db.delete(report)
    db.commit()
    return RedirectResponse("/admin/reports", status_code=303)


def _apply_status(request: Request, db: Session, report_id: int, new_status: str, detail: str = "") -> RedirectResponse:
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    report = db.get(Report, report_id)
    if report is None:
        return RedirectResponse("/admin/reports", status_code=303)
    report.status = new_status
    if new_status == Report.STATUS_REJECTED:
        report.reject_reason = detail
    if new_status == Report.STATUS_PROCESSED:
        report.process_result = detail
    _log(db, admin, new_status if new_status != Report.STATUS_PROCESSED else "process",
         target=Report, target_id=report.id, detail=detail or "（无备注）")
    db.commit()
    return RedirectResponse("/admin/reports", status_code=303)


@router.post("/report/{report_id}/approve")
def approve(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    return _apply_status(request, db, report_id, Report.STATUS_APPROVED, "审核通过，允许上墙公示")


@router.post("/report/{report_id}/reject")
def reject(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)],
           reason: Annotated[str, Form()] = ""):
    return _apply_status(request, db, report_id, Report.STATUS_REJECTED, reason or "未说明")


@router.post("/report/{report_id}/transfer")
def transfer(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)],
             reason: Annotated[str, Form()] = ""):
    return _apply_status(request, db, report_id, Report.STATUS_TRANSFERRED, reason or "已转交相关部门")


@router.post("/report/{report_id}/process")
def process(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)],
            result: Annotated[str, Form()]):
    return _apply_status(request, db, report_id, Report.STATUS_PROCESSED, result)


@router.get("/logs")
def logs_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    logs = db.scalars(select(Log).order_by(Log.created_at.desc()).limit(200)).all()
    return _tpl(request, "admin/logs.html", admin=admin, logs=logs, cur_page="logs")
