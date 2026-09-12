"""FastAPI 应用入口。

启动方式（项目根目录）：
    python run.py
或：
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .database import Base, engine
from .migrate import run_migrations
from .routers import admin, public
from .seed import run_seed

config.ensure_dirs()

app = FastAPI(title=config.APP_NAME, version=config.VERSION)

app.add_middleware(SessionMiddleware, secret_key=config.load_secret_key())

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.mount("/media", StaticFiles(directory=config.MEDIA_DIR), name="media")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app.state.templates = templates
app.state.app_name = config.APP_NAME
app.state.motto = config.MOTTO

# 站点图标：优先静态目录 favicon；不存在时由页面内联 SVG 兜底。
app.include_router(public.router)
app.include_router(admin.router)


@app.on_event("startup")
def _startup() -> None:
    """建表 + 迁移（加列/品牌同步）+ 种子数据（全部幂等）。"""
    Base.metadata.create_all(bind=engine)
    run_migrations()
    run_seed()


@app.exception_handler(404)
async def not_found_handler(request, exc):  # noqa: ANN001
    """兜底：未匹配路径统一回首页。"""
    return RedirectResponse("/")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
