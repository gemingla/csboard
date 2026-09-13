"""cs榜 · CSBOARD 一键启动器（PyInstaller 入口）。

双击 exe 即：
  1. 首次运行 → 引导设置管理员账号与密码
  2. 自动选择空闲端口 → 启动本地服务 → 自动打开浏览器
  3. 后台静默检查更新（抓取 GitHub 最新 Release，抓到就下载并在退出后自动替换）

数据（SQLite、素材、密钥）保存在 exe 同级的 data/ 目录，绿色免安装。

环境变量：
    CSBOARD_HOST         监听地址（默认 127.0.0.1；设为 0.0.0.0 可让局域网访问）
    CSBOARD_PORT         指定端口（默认自动从 8000 起找空闲端口）
    CSBOARD_NO_BROWSER   设为 1 不自动打开浏览器
    CSBOARD_NO_UPDATE    设为 1 关闭自动更新检查
    CSBOARD_AUTO_UPDATE  设为 1 时静默自动重启应用更新（默认仅下载并提示）
    BB_ADMIN_USER / BB_ADMIN_PASSWORD  跳过首次引导，直接使用指定管理员账号
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

REPO = "gemingla/csboard"          # 自动更新来源
IS_FROZEN = getattr(sys, "frozen", False)
EXE_PATH = Path(sys.executable) if IS_FROZEN else Path("csboard.exe")
STAGED_PREFIX = ".csboard_"        # 更新暂存文件前缀（新版本先以此名启动，再自改名）


def _setup_console() -> None:
    """让 Windows 控制台/管道输出 UTF-8，避免 ✓ 等字符触发 UnicodeEncodeError。"""
    if os.name == "nt":
        try:
            os.system("chcp 65001 >nul 2>nul")
        except Exception:  # noqa: BLE001
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass


def _promote_staged() -> None:
    """不再使用（保留占位：PyInstaller onefile 不允许运行中的 exe 被改名）。

    实测：onefile 打包的 exe 被改名后，bootloader 会在延迟加载模块时报
    "appears to have been moved or deleted" 并退出。因此更新改为
    「旧进程退出后由批处理替换文件」的方案，见 _apply_update。
    """


def _cleanup_update_residue() -> None:
    """清理更新过程残留（.exe.new / 更新脚本 / 历史暂存文件）。"""
    if not IS_FROZEN:
        return
    folder = EXE_PATH.parent
    patterns = ["*.exe.new", "_csboard_update.bat", "_csboard_selfupdate.bat",
                f"{STAGED_PREFIX}*.exe"]
    for pattern in patterns:
        for leftover in folder.glob(pattern):
            if leftover.resolve() == EXE_PATH.resolve():
                continue
            try:
                leftover.unlink()
            except OSError:
                pass


# --------------------------------------------------------------------- 基础
def _setup_ssl() -> None:
    """确保 HTTPS 有可用证书链：打包环境常缺系统证书，优先使用随包携带的 certifi。"""
    try:
        import certifi  # type: ignore
        path = certifi.where()
        if os.path.exists(path):
            os.environ.setdefault("SSL_CERT_FILE", path)
            os.environ.setdefault("REQUESTS_CA_BUNDLE", path)
    except Exception:  # noqa: BLE001
        pass


def diagnose() -> None:
    """诊断模式（CSBOARD_DIAGNOSE=1）：打印更新检查的完整过程与错误。"""
    _setup_console()
    _setup_ssl()
    print("[诊断] Python:", sys.version.split()[0])
    print("[诊断] frozen:", IS_FROZEN, "| executable:", sys.executable)
    print("[诊断] SSL_CERT_FILE:", os.environ.get("SSL_CERT_FILE", "(未设置)"))
    try:
        import ssl
        print("[诊断] 默认证书路径:", ssl.get_default_verify_paths())
    except Exception as exc:  # noqa: BLE001
        print("[诊断] ssl 模块信息获取失败:", exc)
    try:
        import certifi  # type: ignore
        print("[诊断] certifi:", certifi.where(), "存在:", os.path.exists(certifi.where()))
    except Exception as exc:  # noqa: BLE001
        print("[诊断] certifi 不可用:", exc)
    try:
        latest = _fetch_latest()
        print("[诊断] 抓取 GitHub Release 成功:", latest)
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("[诊断] 抓取失败:", type(exc).__name__, exc)


def find_free_port(preferred: int = 8000, tries: int = 30) -> int:
    """从 preferred 开始找一个空闲端口；都被占用则由系统分配。"""
    for port in range(preferred, preferred + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def banner(url: str, data_dir: str, app_name: str, version: str) -> None:
    line = "=" * 60
    print(line)
    print(f"  {app_name}  ·  CSBOARD   v{version}")
    print(line)
    print(f"  访问地址 : {url}")
    print(f"  管理后台 : {url}/admin/login")
    print(f"  数据目录 : {data_dir}")
    print("  停止服务 : 按 Ctrl + C，或直接关闭本窗口")
    print(line)
    print("  提示：把 mp4 放进 data/media/ 即可出现在左右献唱位")
    print(line)
    sys.stdout.flush()


# ------------------------------------------------------- 首次运行：设置管理员
def first_run_setup(db_path: Path) -> None:
    """数据库不存在 → 引导设置管理员账号密码（可用环境变量跳过）。"""
    if os.environ.get("BB_ADMIN_PASSWORD"):
        return
    if db_path.exists():
        return
    print("=" * 60)
    print("  首次运行 · 请设置管理员账号（用于登录 /admin/ 管理榜单）")
    print("=" * 60)
    interactive = sys.stdin is not None and sys.stdin.isatty()
    if not interactive:
        print("  （非交互环境：使用默认账号 admin / admin123456，请登录后及时改密）")
        return
    try:
        username = input("  管理员用户名 [admin]：").strip() or "admin"
        while True:
            import getpass
            pwd1 = getpass.getpass("  管理员密码（至少 6 位）：").strip()
            if len(pwd1) < 6:
                print("  [x] 密码太短，至少 6 位，请重新输入")
                continue
            pwd2 = getpass.getpass("  再输一次确认：").strip()
            if pwd1 != pwd2:
                print("  [x] 两次输入不一致，请重新输入")
                continue
            break
    except (KeyboardInterrupt, EOFError):
        print("\n  已跳过，使用默认账号 admin / admin123456")
        return
    os.environ["BB_ADMIN_USER"] = username
    os.environ["BB_ADMIN_PASSWORD"] = pwd1
    print(f"  [OK] 管理员账号已设为 {username}，启动后即可用该账号登录管理台")
    print("=" * 60)


# ------------------------------------------------------------------ 自动更新
def _parse_version(text: str) -> tuple:
    parts = []
    for chunk in str(text).lstrip("vV").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _fetch_latest(timeout: int = 7) -> tuple[str, str] | None:
    """读取 GitHub 最新 Release：返回 (下载地址, 版本号)；失败返回 None。"""
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    req = urllib.request.Request(url, headers={
        "User-Agent": "csboard-updater",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    tag = str(data.get("tag_name", "")).strip()
    for asset in data.get("assets", []):
        name = str(asset.get("name", ""))
        if name.lower().endswith(".exe"):
            return str(asset.get("browser_download_url", "")), tag
    return None


def _apply_update(new_file: Path) -> bool:
    """写一个批处理：等旧进程退出后替换 exe 并启动新版本。

    为什么要绕这一圈：Windows 不允许覆盖/删除正在运行的 exe；
    而 PyInstaller onefile 的 exe 一旦被改名/移动，bootloader 会立刻报错退出。
    所以唯一稳妥的做法是「退出后由外部脚本替换文件」。
    脚本用 ping 做延时（timeout 在无交互 stdin 时会直接失败）。
    """
    exe = EXE_PATH
    script_path = exe.parent / "_csboard_update.bat"
    name = exe.name
    body = (
        "@echo off\r\n"
        "ping -n 3 127.0.0.1 >nul\r\n"
        ":wait\r\n"
        f'tasklist /FI "IMAGENAME eq {name}" 2>NUL | find /I "{name}" >NUL\r\n'
        "if not errorlevel 1 (ping -n 2 127.0.0.1 >nul & goto wait)\r\n"
        f'move /Y "{new_file.name}" "{name}" >nul 2>NUL\r\n'
        # 新版本启动时清掉更新开关，避免反复触发更新循环
        "set CSBOARD_FORCE_UPDATE=\r\n"
        "set CSBOARD_AUTO_UPDATE=\r\n"
        f'start "" "{name}"\r\n'
        'del "%~f0" >nul 2>NUL\r\n'
    )
    try:
        script_path.write_text(body, encoding="gbk", errors="replace")
        subprocess.Popen(
            ["cmd", "/c", str(script_path)],
            cwd=str(exe.parent),
            stdin=subprocess.DEVNULL,
            creationflags=(getattr(subprocess, "DETACHED_PROCESS", 0)
                           | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)),
            close_fds=True,
        )
        return True
    except OSError:
        return False


def check_update(current_version: str, quiet: bool = True) -> None:
    """后台检查更新：抓到新版本就下载（可选自动替换重启）；任何失败都静默跳过。"""
    if os.environ.get("CSBOARD_NO_UPDATE") == "1":
        return
    force = os.environ.get("CSBOARD_FORCE_UPDATE") == "1"
    try:
        _setup_ssl()
        latest = _fetch_latest()
        if not latest:
            return
        url, tag = latest
        if not url:
            return
        if not force and _parse_version(tag) <= _parse_version(current_version):
            return
        print(f"\n[更新] {'强制更新' if force else '发现新版本'} {tag}（当前 v{current_version}），正在下载…")
        target = EXE_PATH.with_suffix(".exe.new") if IS_FROZEN else Path("csboard.exe.new")
        urllib.request.urlretrieve(url, target)
        print(f"[更新] 下载完成：{target.name}")
        if os.environ.get("CSBOARD_AUTO_UPDATE") == "1" and IS_FROZEN:
            if _apply_update(target):
                print("[更新] 正在重启以应用新版本…（窗口会自行关闭）\n")
                time.sleep(1)
                os._exit(0)
            print("[更新] 自动替换未启动，请手动把 csboard.exe.new 改名覆盖 csboard.exe\n")
        else:
            print("[更新] 新版本已下载（csboard.exe.new）：")
            print("[更新]   · 设 CSBOARD_AUTO_UPDATE=1 可让程序自动替换并重启")
            print("[更新]   · 或手动关闭本窗口后，把 .new 文件改名覆盖 csboard.exe\n")
    except Exception as exc:  # noqa: BLE001 —— 网络/权限/环境任何问题都只跳过
        if not quiet:
            print(f"[更新] 已跳过（{type(exc).__name__}: {exc}）")


# -------------------------------------------------------------------- 主流程
def main() -> None:
    _setup_console()
    if os.environ.get("CSBOARD_DIAGNOSE") == "1":
        diagnose()
        return
    _cleanup_update_residue()
    _setup_ssl()
    host = os.environ.get("CSBOARD_HOST", "127.0.0.1")
    env_port = os.environ.get("CSBOARD_PORT", "").strip()
    port = int(env_port) if env_port.isdigit() else find_free_port()
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"

    from app import config          # 轻量导入：不触发建表
    first_run_setup(Path(config.DB_PATH))

    from app.main import app        # 导入即注册路由；建表/种子在 startup 事件

    banner(url, str(config.DATA_DIR), config.APP_NAME, config.VERSION)

    if os.environ.get("CSBOARD_NO_BROWSER") != "1":
        threading.Timer(1.6, lambda: webbrowser.open(url)).start()

    threading.Thread(target=check_update, args=(config.VERSION,), daemon=True).start()

    import uvicorn
    try:
        uvicorn.run(app, host=host, port=port, log_level="info",
                    loop="asyncio", http="h11")
    except KeyboardInterrupt:
        pass
    finally:
        print("\ncs榜 已停止，数据已保存到 data/ 目录。")


if __name__ == "__main__":
    main()
