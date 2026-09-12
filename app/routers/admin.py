"""管理员路由：登录、工作台、榜单管理（增删改/排序/批量导入）、设置（改密）、操作日志。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import VERSION
from ..database import get_db
from ..models import Admin, Board, Log, Report
from ..security import current_admin, hash_password, verify_password

router = APIRouter(prefix="/admin")


def _tpl(request: Request, name: str, **ctx):
    return request.app.state.templates.TemplateResponse(
        request=request, name=name,
        context={"app_name": request.app.state.app_name,
                 "motto": request.app.state.motto, "version": VERSION, **ctx},
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
        "total": db.scalar(select(func.count()).select_from(Report)) or 0,
        "approved": db.scalar(select(func.count()).select_from(Report).where(Report.status == Report.STATUS_APPROVED)) or 0,
        "heat": db.scalar(select(func.coalesce(func.sum(Report.heat), 0))) or 0,
    }
    recent = db.scalars(
        select(Report).order_by(Report.created_at.desc()).limit(12)
    ).all()
    return _tpl(request, "admin/dashboard.html", admin=admin, stats=stats,
                recent=recent, cur_page="dashboard")


@router.get("/reports")
def reports_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    stmt = select(Report).order_by(Report.sort_order.asc(), Report.heat.desc())
    reports = db.scalars(stmt).all()
    boards = db.scalars(select(Board).where(Board.is_active == True).order_by(Board.sort_order)).all()  # noqa: E712
    return _tpl(request, "admin/reports.html", admin=admin, reports=reports,
                boards=boards, cur_page="reports")


def _next_sort_order(db: Session) -> int:
    """新条目排到末尾（sort_order 以 10 递增，方便中间插入）。"""
    current_max = db.scalar(select(func.max(Report.sort_order))) or 0
    return int(current_max) + 10


@router.post("/reports/add-fast")
def add_fast(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    who: Annotated[str, Form()],
    reason: Annotated[str, Form()] = "",
    heat: Annotated[str, Form()] = "0",
):
    """快速添加：一行完成 —— 姓名(必填)+事迹(可选)+围观指数(可选)。
    标题自动生成为「cs榜 · 姓名」；返回后停留在后台并聚焦姓名框，支持连续录入。"""
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
        title=f"cs榜 · {name}"[:120],
        who=name,
        reason=reason,
        heat=heat_val,
        sort_order=_next_sort_order(db),
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
        sort_order=_next_sort_order(db),
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
    """（保留方法：供将来审核流复用；当前界面已无使用。）"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    report = db.get(Report, report_id)
    if report is None:
        return RedirectResponse("/admin/reports", status_code=303)
    report.status = new_status
    _log(db, admin, "status", target=Report, target_id=report.id, detail=detail or "（无备注）")
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


# ---------------------------------------------------------------- 条目编辑
@router.get("/report/{report_id}/edit")
def edit_page(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    report = db.get(Report, report_id)
    if report is None:
        return RedirectResponse("/admin/reports", status_code=303)
    boards = db.scalars(select(Board).where(Board.is_active == True).order_by(Board.sort_order)).all()  # noqa: E712
    return _tpl(request, "admin/edit.html", admin=admin, report=report,
                boards=boards, cur_page="reports")


@router.post("/report/{report_id}/edit")
def edit_save(
    report_id: int,
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
    """保存条目修改（标题/姓名/事迹/指数/时间/地点/所属榜单）。"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    report = db.get(Report, report_id)
    if report is None:
        return RedirectResponse("/admin/reports", status_code=303)
    try:
        heat_val = max(0, int(heat or 0))
    except ValueError:
        heat_val = 0
    report.title = (title or report.title)[:120]
    report.who = (who or "匿名")[:80]
    report.reason = reason
    report.heat = heat_val
    report.happened_at = happened_at[:40]
    report.location = location[:120]
    if board:
        board_obj = db.scalar(select(Board).where(Board.slug == board))
        if board_obj is not None:
            report.board_id = board_obj.id
    _log(db, admin, "edit", target=Report, target_id=report.id, detail=f"编辑条目: {report.title}")
    db.commit()
    return RedirectResponse("/admin/reports", status_code=303)


# ---------------------------------------------------------------- 手动排序
@router.post("/report/{report_id}/move")
def move_report(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)],
                action: Annotated[str, Form()]):
    """手动排序：up / down / top / bottom，重排后按 10 递增归一化。"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    reports = list(db.scalars(select(Report).order_by(Report.sort_order.asc(), Report.heat.desc())))
    idx = next((i for i, r in enumerate(reports) if r.id == report_id), None)
    if idx is None:
        return RedirectResponse("/admin/reports", status_code=303)
    if action == "up" and idx > 0:
        reports[idx - 1], reports[idx] = reports[idx], reports[idx - 1]
    elif action == "down" and idx < len(reports) - 1:
        reports[idx + 1], reports[idx] = reports[idx], reports[idx + 1]
    elif action == "top":
        reports.insert(0, reports.pop(idx))
    elif action == "bottom":
        reports.append(reports.pop(idx))
    for i, r in enumerate(reports, start=1):
        r.sort_order = i * 10
    _log(db, admin, "sort", target=Report, target_id=report_id, detail=f"手动排序: {action}")
    db.commit()
    return RedirectResponse("/admin/reports", status_code=303)


# ---------------------------------------------------------------- 批量导入
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5")


def _decode_payload(raw: bytes) -> str:
    """按 utf-8-sig → utf-8 → gb18030 → big5 依次探测解码。

    Excel 中文版导出的 CSV 通常是 GBK/ANSI 编码，若只按 UTF-8 解码会整列乱码。
    """
    for enc in ENCODINGS:
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if "\ufffd" not in text:
            return text
    return raw.decode("utf-8", errors="replace")


def _split_csv_line(line: str, sep: str) -> list[str]:
    """按标准 CSV 规则切分单行：支持双引号包裹（引号内分隔符不分割、"" 表示一个引号）。"""
    if '"' not in line:
        return [p.strip() for p in line.split(sep)]
    fields: list[str] = []
    buf: list[str] = []
    in_quote = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quote:
            if ch == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    buf.append('"')
                    i += 2
                    continue
                in_quote = False
                i += 1
                continue
            buf.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quote = True
            i += 1
            continue
        if ch == sep:
            fields.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    fields.append("".join(buf).strip())
    return fields


def _split_line(line: str) -> list[str]:
    """选择分隔符切分一行：制表符 > 英文逗号（走 CSV 引号规则）> 中文逗号 / 竖线。"""
    if "\t" in line:
        return _split_csv_line(line, "\t")
    if "," in line:
        return _split_csv_line(line, ",")
    for sep in ("，", "|"):
        if sep in line:
            return [p.strip() for p in line.split(sep)]
    return [line.strip()]


def _parse_import_text(text: str) -> list[dict]:
    """解析批量导入文本：每行「姓名[,事迹[,指数]]」。

    - 分隔符：制表符 / 英文逗号 / 中文逗号 / 竖线（可直接从 Excel 粘贴）
    - 支持 CSV 引号包裹字段；首行「姓名」表头自动跳过；# 开头的行是注释
    """
    rows: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        parts = _split_line(line)
        who = (parts[0] or "").strip().strip('"').strip()
        if not who:
            continue
        if who in ("姓名", "名字", "who", "name"):
            continue
        reason = parts[1].strip() if len(parts) > 1 else ""
        heat_raw = parts[2].strip() if len(parts) > 2 else "0"
        # 指数容错：允许 "1,234" 这类千分位写法
        heat_raw = heat_raw.replace(",", "").replace("，", "").strip()
        try:
            heat_val = max(0, int(heat_raw or 0))
        except ValueError:
            heat_val = 0
        rows.append({"who": who[:60], "reason": reason, "heat": heat_val})
    return rows


@router.get("/import")
def import_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    return _tpl(request, "admin/import.html", admin=admin, cur_page="import", error=None)


@router.post("/import")
def import_do(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    text: Annotated[str, Form()] = "",
    csv_file: Annotated[UploadFile | None, File()] = None,
):
    """批量导入榜单成员：优先使用上传的 CSV/TXT 文件，否则用粘贴的文本。"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    board_obj = db.scalar(select(Board).order_by(Board.sort_order).limit(1))
    if board_obj is None:
        return RedirectResponse("/admin/reports", status_code=303)

    payload = ""
    if csv_file is not None and csv_file.filename:
        try:
            payload = _decode_payload(csv_file.file.read())
        except Exception:
            payload = ""
    if not payload.strip():
        payload = text or ""

    rows = _parse_import_text(payload)
    if not rows:
        return _tpl(request, "admin/import.html", admin=admin, cur_page="import",
                    error="没有解析到任何有效行。请检查格式：每行「姓名,事迹,指数」。")

    order = _next_sort_order(db) - 10
    for row in rows:
        order += 10
        db.add(Report(
            board_id=board_obj.id,
            title=f"cs榜 · {row['who']}"[:120],
            who=row["who"],
            reason=row["reason"],
            heat=row["heat"],
            sort_order=order,
            status=Report.STATUS_APPROVED,
        ))
    _log(db, admin, "import", target=Report, detail=f"批量导入 {len(rows)} 人")
    db.commit()
    return RedirectResponse(f"/admin/reports?imported={len(rows)}", status_code=303)


# ---------------------------------------------------------------- 设置（改密）
@router.get("/settings")
def settings_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    return _tpl(request, "admin/settings.html", admin=admin, cur_page="settings",
                error=None, ok=None)


@router.post("/settings/password")
def change_password(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[str, Form()],
    new: Annotated[str, Form()],
    confirm: Annotated[str, Form()],
):
    """修改管理员密码（校验当前密码 + 两次一致 + 长度 ≥ 6）。"""
    admin = current_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    if not verify_password(current, admin.password_hash):
        return _tpl(request, "admin/settings.html", admin=admin, cur_page="settings",
                    error="当前密码不正确", ok=None)
    if new != confirm:
        return _tpl(request, "admin/settings.html", admin=admin, cur_page="settings",
                    error="两次输入的新密码不一致", ok=None)
    if len(new) < 6:
        return _tpl(request, "admin/settings.html", admin=admin, cur_page="settings",
                    error="新密码至少 6 位", ok=None)
    admin.password_hash = hash_password(new)
    _log(db, admin, "password", target=Admin, target_id=admin.id, detail="修改管理员密码")
    db.commit()
    return _tpl(request, "admin/settings.html", admin=admin, cur_page="settings",
                error=None, ok="密码已更新，下次登录请使用新密码。")
