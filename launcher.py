"""cs榜 · CSBOARD 一键启动器（PyInstaller 入口）。

双击 exe 即：自动选择空闲端口 → 启动本地服务 → 自动打开浏览器。
数据（SQLite、素材、密钥）保存在 exe 同级的 data/ 目录，绿色免安装。

环境变量：
    CSBOARD_HOST       监听地址（默认 127.0.0.1；设为 0.0.0.0 可让局域网访问）
    CSBOARD_PORT       指定端口（默认自动从 8000 起找空闲端口）
    CSBOARD_NO_BROWSER 设为 1 则不自动打开浏览器
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser


def find_free_port(preferred: int = 8000, tries: int = 30) -> int:
    """从 preferred 开始找一个空闲端口；都占用则由系统分配。"""
    for port in range(preferred, preferred + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def banner(url: str, data_dir: str, app_name: str, version: str) -> None:
    line = "=" * 58
    print(line)
    print(f"  {app_name}  ·  CSBOARD   v{version}")
    print(line)
    print(f"  访问地址 : {url}")
    print(f"  管理后台 : {url}/admin/login   （默认 admin / admin123456）")
    print(f"  数据目录 : {data_dir}")
    print("  停止服务 : 按 Ctrl + C，或直接关闭本窗口")
    print(line)
    print("  提示：把 mp4 放到 data/media/ 即可出现在左右献唱位")
    print(line)
    sys.stdout.flush()


def main() -> None:
    host = os.environ.get("CSBOARD_HOST", "127.0.0.1")
    env_port = os.environ.get("CSBOARD_PORT", "").strip()
    port = int(env_port) if env_port.isdigit() else find_free_port()
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"

    # 延迟导入，确保先打印启动信息（打包后导入 uvicorn 需要一点时间）
    from app import config
    from app.main import app

    banner(url, str(config.DATA_DIR), config.APP_NAME, config.VERSION)

    if os.environ.get("CSBOARD_NO_BROWSER") != "1":
        threading.Timer(1.6, lambda: webbrowser.open(url)).start()

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
