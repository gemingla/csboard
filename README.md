# cs榜 · CSBOARD

[![Release](https://img.shields.io/github/v/release/gemingla/csboard?label=release)](https://github.com/gemingla/csboard/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#)

> 把最该感谢的人，挂上最高的榜。

继承原版《好人榜 1.2》（tkinter + PyInstaller）全部灵魂的 Web 系统 ——
搞笑榜单、唱歌视频、"不告老师法则"条款、土味大数分数，加上**点进去看原因的详情页**
与**管理员后台**，做成一键部署、可二次开发的开源项目。

**两种用法**：非开发者下载 exe 双击即用；开发者源码运行 / 自行打包 / 部署到服务器。

---

## 🚀 一键部署（Windows，推荐）

从 **[Releases](https://github.com/gemingla/csboard/releases/latest)** 下载 `csboard.exe`（约 39 MB，免安装）：

| 步骤 | 说明 |
|---|---|
| 1️⃣ 双击运行 | 自动选择空闲端口 → 启动服务 → 自动打开浏览器 |
| 2️⃣ 开始录榜 | 登录 `/admin/login`（`admin / admin123456`）→ 快速添加或批量导入 |
| 3️⃣ 数据在哪 | 全部在 exe 同级的 `data/` 目录（绿色版，拷走该目录即完成迁移/备份） |
| 4️⃣ 带上歌声 | 在 exe 旁建 `video/` 放 mp4，或把 mp4 丢进 `data/media/`（取前两个轮流播放） |

**环境变量**（可选）：

```bat
set CSBOARD_HOST=0.0.0.0     :: 允许局域网访问（同网段设备访问 http://你的IP:端口）
set CSBOARD_PORT=8080        :: 指定端口（默认从 8000 起自动找空闲）
set CSBOARD_NO_BROWSER=1     :: 启动时不自动打开浏览器
set BB_ADMIN_PASSWORD=xxx    :: 首次生成管理员账号时使用该密码
```

> 首次启动会创建 `data/beastboard.db` 与管理员账号 —— 请登录后到 **设置** 页改成自己的密码。

---

## 💻 源码运行（开发者）

```bash
pip install -r requirements.txt
python run.py            # 或 uvicorn app.main:app --reload
# 打开 http://127.0.0.1:8000
```

- 初始为**空榜**：榜单成员全部由管理员在后台录入
- 默认管理员：`admin / admin123456`（可用环境变量 `BB_ADMIN_USER` / `BB_ADMIN_PASSWORD` 覆盖）
- 视频素材：把 mp4 放进 `data/media/` 即出现在左右献唱位

## 🛠 自行打包 exe

```bash
pip install pyinstaller
pyinstaller --onefile --name csboard \
  --add-data "app/templates;app/templates" --add-data "app/static;app/static" \
  --hidden-import uvicorn.protocols.http.h11_impl \
  --hidden-import uvicorn.loops.asyncio --hidden-import uvicorn.lifespan.on \
  --collect-submodules uvicorn \
  --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide6 \
  --exclude-module tkinter --exclude-module matplotlib --exclude-module pandas \
  launcher.py
# 产物：dist/csboard.exe（约 39 MB 单文件）
```

> 若本机同时装了多个 Qt 绑定（PyQt5/PyQt6），必须像上面那样 `--exclude-module` 排除，否则构建会中断。

## 🌐 服务器部署

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

配合 Nginx/Caddy 反代与 HTTPS 即可公网使用；数据库默认 SQLite，改 `app/database.py` 连接串可切 PostgreSQL。

---

## ✨ 特性

### 前台
- **三栏舞台**：左右两边献唱视频**轮流播放**（20 秒一换、互斥暂停、点击才开播），中央排行榜**竖向排列**
- **点进去看原因**：详情页展示上榜原因（时间 / 地点 / 事迹）+ 「顶一下」围观 +1
- 前三名奖牌高亮，围观指数大数滚动（继承原版"土味大数"梗）
- **丝滑动画层**：入场交错浮现、背景光斑跟随鼠标、榜单行光带跟随、按钮涟漪、滚动进度条、
  奖牌弹入、献唱呼吸光晕 —— 并遵循系统「减少动态效果」偏好
- 进场条款弹窗（"不告老师法则"）、键盘彩蛋 **B-E-A-S-T**、关于页
- 樱花莓果液态玻璃主题，全站**手写 CSS / JS，零外部 CDN**，可完全离线运行

### 管理后台（cs榜由你掌控）
| 能力 | 说明 |
|---|---|
| 🔐 登录 / 改密 | PBKDF2-SHA256 加盐哈希存储 |
| ⚡ 快速添加 | 一行「姓名 + 事迹 + 指数」回车即上榜，标题自动生成，可连续录入 |
| 📥 批量导入 | 粘贴名单（英文/中文逗号、制表符、竖线，可直接从 Excel 粘贴）或上传 CSV/TXT；**自动识别 GBK/UTF-8 编码** |
| ✏️ 条目编辑 | 标题 / 姓名 / 事迹 / 指数 / 时间 / 地点 / 所属榜单 |
| 🔀 手动排序 | ↑ ↓ ⤒ 置顶 —— 名次由管理员说了算，不再只看指数 |
| 🗑️ 删除 | 带确认提示 |
| 📜 操作日志 | 谁在何时对什么做了什么，全程留痕 |
| 📊 工作台 | 榜单总人数 / 已上墙 / 总围观指数统计 |

---

## 📁 项目结构

```
csboard/
├── launcher.py           # exe 一键启动器（自动选端口 + 开浏览器）
├── run.py                # 源码开发启动（热重载）
├── app/
│   ├── main.py           # FastAPI 入口（路由挂载、中间件、启动建表+迁移+种子）
│   ├── config.py         # 路径（含 frozen 适配）/ 品牌 / 密钥
│   ├── database.py       # SQLAlchemy 引擎与会话
│   ├── models.py         # ORM：Board / Report / Admin / Log
│   ├── security.py       # 密码哈希 + 会话
│   ├── migrate.py        # 轻量迁移（加列 / 品牌同步，幂等）
│   ├── seed.py           # 种子数据（管理员、榜单、视频素材迁移，幂等）
│   ├── routers/
│   │   ├── public.py     # 前台：首页 / 榜单 / 详情 / 围观 / 条款 / 关于
│   │   └── admin.py      # 后台：登录 / 工作台 / 增删改 / 排序 / 批量导入 / 改密 / 日志
│   ├── templates/        # Jinja2 模板（含 admin/）
│   └── static/           # 手写 CSS / JS（无外部依赖）
├── data/                 # 运行时：SQLite + 素材 + 密钥（.gitignore）
├── requirements.txt
└── LICENSE
```

---

## ❓ 常见问题

**Q：双击 exe 没反应 / 一闪而过？**
端口被占用时会自动换端口，若仍失败请检查杀毒软件拦截；可在命令行运行 `csboard.exe` 查看报错信息。

**Q：怎么让同班同学一起看？**
设置 `CSBOARD_HOST=0.0.0.0` 启动，然后用 `ipconfig` 查到本机局域网 IP，
把 `http://你的IP:端口` 发出去（首次需在 Windows 防火墙放行该端口）。

**Q：数据怎么备份 / 换电脑？**
整个 `data/` 目录拷走即可（含数据库、视频、密钥）；放回新机器的 exe 同级目录即恢复。

**Q：忘记管理员密码了？**
用 Python 生成新哈希再写入数据库：

```bash
python -c "import sys; sys.path.insert(0,'.'); from app.security import hash_password; print(hash_password('你的新密码'))"
# 把输出写入 data/beastboard.db 的 admins 表 password_hash 字段（任一 SQLite 工具即可）
```

**Q：Excel 导出的名单导入后是乱码？**
已内置 GBK/ANSI 自动识别；若仍异常，请在 Excel 里另存为「CSV UTF-8」后重新导入。

**Q：想换主色调 / 去掉动画？**
主色在 `app/static/css/app.css` 顶部 `:root` 变量；动画集中在同文件「丝滑动画层」区块，
浏览器开启系统「减少动态效果」时会自动降级为静态。

---

## ⚖️ 合规声明

- 榜单内容由管理员维护，应与事实相符；**不存储身份证号、手机号等敏感个人信息**。
- 管理员操作日志留痕，过程可追溯；请勿将本系统用于人身攻击或侵犯他人权益。

## 🗺 Roadmap

- **v0.3** 揭榜动画（倒计时 / 逐行翻开 / 彩带）、分享海报长图、应援留言墙
- **v0.4** 条目配图与头像、一键备份/恢复、多榜单管理
- **v1.0** Docker 部署、OpenAPI 文档、CI 测试、主题包与多语言

## 📄 License

[MIT](LICENSE) —— 自由使用、修改、分发，保留作者与来源声明即可。

原版程序《好人榜 1.2》作者：**3605268328**。本项目继承其创意并重制为 Web 系统。
