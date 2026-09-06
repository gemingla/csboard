# 畜牲榜 · BeastBoard

> 把最该感谢的人，挂上最高的榜。

继承原版《好人榜 1.2》（tkinter + PyInstaller）全部灵魂的 Web 系统：
搞笑榜单、唱歌视频、"不告老师法则"条款、土味大数分数 —— 加上
**看原因详情页** 与 **管理员审核系统**，做成可部署、可二次开发的开源项目。

## 功能（v0.1）

- 首页多榜单卡片墙（好人榜 / 曝光榜），前三名奖牌高亮，围观指数数字滚动（继承 exe 大数梗）
- 详情页：**点进去看上榜原因**（时间 / 地点 / 经过 / 处理结果 / 围观 +1）
- 匿名提交：投递到曝光榜（待审核队列），界面明确提示"只描述行为，不公开实名"
- 管理员系统：登录 → 工作台统计 → 审核队列（通过 / 驳回 / 转交 / 处理回填）→ 操作日志
- 献唱点歌台：自动加载 `data/media/*.mp4`（预置 yt.mp4、闫涛10.mp4）
- 进场条款弹窗（继承"不告老师法则"，接受后才进入）
- 键盘彩蛋（B-E-A-S-T）、关于页
- 全部样式手写，**零外部 CDN**，可离线部署

## 快速开始

```bash
pip install -r requirements.txt
python run.py
# 打开 http://127.0.0.1:8000
```

种子数据自动生成：2 个榜单、好人榜 7 人（原版数据迁移）、曝光榜 2 条示例事件、
管理员 `admin / admin123456`（可用环境变量覆盖：`BB_ADMIN_USER` / `BB_ADMIN_PASSWORD`）。

视频素材：将 mp4 放入 `data/media/` 即出现在点歌台；首次运行会尝试从发布目录迁移。

## 部署

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docker 化（v1.0 提供）＆ PostgreSQL 切换（SQLAlchemy，改 `database.py` 连接串即可）。

## 项目结构

```
beastboard/
├── app/
│   ├── main.py        # FastAPI 入口（路由挂载、中间件、启动建表+种子）
│   ├── config.py      # 路径 / 配置 / 密钥
│   ├── database.py    # SQLAlchemy 引擎与会话
│   ├── models.py      # ORM：Board / Report / Admin / Log
│   ├── security.py    # 密码哈希 + 会话
│   ├── seed.py        # 种子数据（幂等）
│   ├── routers/
│   │   ├── public.py  # 前台：首页/榜单/详情/提交/条款/关于
│   │   └── admin.py   # 后台：登录/工作台/审核/日志
│   ├── templates/     # Jinja2 模板（含 admin/）
│   └── static/        # 手写 CSS / JS（无外部依赖）
├── data/              # 运行时：SQLite + 素材（gitignore）
├── run.py             # 开发启动（reload）
└── requirements.txt
```

## 合规红线（重要）

- 曝光榜 **只描述行为**，被反映对象仅存特征描述；**禁止**存储姓名、身份证号、
  照片、手机号等可直接识别个人的信息。（《个人信息保护法》第 28 条）
- 管理员审核流 + 操作日志留痕，确保"先审后上、过程可追溯"。

## Roadmap

- v0.2 证据上传、围观数据细化、管理员改密、导出台账
- v0.3 揭榜动画、分享海报、吐槽墙、条款彩蛋
- v1.0 Docker 部署文档、OpenAPI、README 完善、开源发布

## License

MIT（见 LICENSE）—— 自由使用、修改、分发；保留作者与项目来源声明即可。
