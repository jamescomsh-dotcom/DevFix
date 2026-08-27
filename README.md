# DevFix

DevFix 是一个使用 FastAPI、SQLAlchemy AsyncSession、MySQL 和 Alembic 构建的异步后端项目，用于记录开发问题、AI 或人工解决方案、验证结果与最终有效解法。

当前完成 **阶段 0 的本地代码部分**。本阶段只建立可运行、可测试的 FastAPI 骨架，不连接数据库，也不会在应用启动时创建表。Git 分支、commit、GitHub 仓库和 Pull Request 尚未执行。

## 当前能力

- `GET /health`：返回 `{"status": "ok"}`。
- `GET /docs`：打开 FastAPI 自动生成的 Swagger UI。
- `GET /openapi.json`：读取 OpenAPI 描述。
- 自动化测试覆盖以上启动验收点。

## 环境要求

- Python 3.14
- MySQL（从阶段 1 开始需要）

项目当前使用的直接依赖已固定在 `requirements.txt`。异步 MySQL 驱动选择 `asyncmy`，数据库 URL 格式见 `.env.example`。

## 本地启动

在 PowerShell 中进入项目目录后执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

然后访问：

- Swagger UI：<http://127.0.0.1:8001/docs>
- 健康检查：<http://127.0.0.1:8001/health>

本机的 TCP 8000 已被 Windows 排除，直接使用 Uvicorn 默认端口会触发 `WinError 10013`，因此开发端口固定使用 8001。

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 当前目录

```text
app/
├── main.py
├── models/
├── routers/
│   └── health.py
├── schemas/
│   └── health.py
└── services/
docs/
├── ai-development-log.md
└── project-design.md
tests/
├── conftest.py
└── test_health.py
```

Router 负责 HTTP 输入输出，Service 负责业务规则与事务，Model 负责 SQLAlchemy 映射，Schema 负责请求和响应验证。阶段 0 只有系统健康接口，因此业务 Service 和数据库 Model 暂时为空。

## 开发阶段

1. 阶段 0：需求与仓库初始化、`/health`。
2. 阶段 1：异步 Engine、Session 工厂和数据库依赖。
3. 阶段 2：三张业务表及首条 Alembic 迁移。
4. 阶段 3：项目 CRUD。
5. 阶段 4：问题 CRUD。
6. 阶段 5：解决尝试与接受方案事务闭环。
7. 阶段 6：筛选、分页、搜索和统计。
8. 阶段 7：文档、演示和收尾。

下一步是阶段 1。开始前需要先确认本机 MySQL 的服务、版本、端口与可用数据库账号；该检查应先只读进行。

## 设计资料

- [项目设计基线](docs/project-design.md)
- [AI 开发日志](docs/ai-development-log.md)
