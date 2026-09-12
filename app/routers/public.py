"""公共（前台）路由：首页（cs榜）、详情页（看原因）、围观、条款。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import MEDIA_DIR, VERSION
from ..database import get_db
from ..models import Board, Report

router = APIRouter()

TERMS_TEXT = """使用条款：
1. 您同意遵循不告老师法则。
2. 上榜内容由管理员维护，接受所有人监督。
3. 恶意抹黑、造谣生事者将被请出本榜。
4. 使用本应用即表示您同意以上条款。"""


def _tpl(request: Request, name: str, **ctx):
    return request.app.state.templates.TemplateResponse(
        request=request, name=name,
        context={"app_name": request.app.state.app_name,
                 "motto": request.app.state.motto, "version": VERSION, **ctx},
    )


def _videos() -> list[dict]:
    """data/media 下的视频素材（v0.1 仅做展示与点播）。"""
    items = []
    try:
        for p in sorted(MEDIA_DIR.glob("*.mp4")):
            items.append({"name": p.name, "url": f"/media/{p.name}"})
    except OSError:
        pass
    return items


@router.get("/")
def index(request: Request, db: Annotated[Session, Depends(get_db)]):
    boards = db.scalars(
        select(Board).where(Board.is_active == True).order_by(Board.sort_order)  # noqa: E712
    ).all()
    sections = []
    for board in boards:
        reports = db.scalars(
            select(Report).where(Report.board_id == board.id,
                                 Report.status.in_(["approved", "processed", "transferred"]))
            .order_by(Report.sort_order.asc(), Report.heat.desc())
        ).all()
        sections.append({"board": board, "reports": reports})
    return _tpl(request, "index.html",
                sections=sections, active_slug=None,
                videos=_videos(),
                show_terms=not request.session.get("terms_ok"),
                terms_text=TERMS_TEXT)


@router.get("/about")
def about(request: Request):
    return _tpl(request, "about.html", active_slug=None)


@router.post("/terms/accept")
def terms_accept(request: Request):
    request.session["terms_ok"] = True
    return RedirectResponse("/", status_code=303)


@router.get("/terms-rejected")
def terms_rejected(request: Request):
    return HTMLResponse(
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>条款</title>"
        "<style>body{background:#fdf2f7;color:#4a2b4a;font-family:system-ui;"
        "display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
        "div{text-align:center}p{color:#8b6b85}a{color:#e8467c}</style></head><body>"
        "<div><h1 style='color:#c3326a'>那……先别看了</h1><p>不接受条款的话，本榜暂不开放。想好了再来。</p>"
        "<p><a href='/'>返回首页</a></p></div></body></html>"
    )


@router.get("/board/{slug}")
def board_page(slug: str, request: Request, db: Annotated[Session, Depends(get_db)]):
    board = db.scalar(select(Board).where(Board.slug == slug, Board.is_active == True))  # noqa: E712
    if board is None:
        return RedirectResponse("/", status_code=303)
    reports = db.scalars(
        select(Report).where(Report.board_id == board.id,
                             Report.status.in_(["approved", "processed", "transferred"]))
        .order_by(Report.sort_order.asc(), Report.heat.desc())
    ).all()
    return _tpl(request, "board.html", board=board, reports=reports, active_slug=slug)


@router.get("/report/{report_id}")
def report_detail(report_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    report = db.get(Report, report_id)
    if report is None:
        return RedirectResponse("/", status_code=303)
    evidence = []
    if report.evidence and report.evidence != "[]":
        import json as _json
        try:
            evidence = _json.loads(report.evidence)
        except Exception:
            evidence = []
    return _tpl(request, "detail.html", report=report, evidence=evidence, active_slug=report.board.slug)


@router.post("/report/{report_id}/heat")
def add_heat(report_id: int, db: Annotated[Session, Depends(get_db)]):
    """围观 +1（保留 exe 大数分数的“看热闹”感）。"""
    report = db.get(Report, report_id)
    if report is not None:
        report.heat += 1
        db.commit()
    return RedirectResponse(f"/report/{report_id}#heat", status_code=303)
