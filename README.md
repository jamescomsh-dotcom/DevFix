# DevFix

DevFix Lite 是一个使用 FastAPI、SQLAlchemy AsyncSession、MySQL 和 Alembic 构建的单表异步 CRUD 后端，用于记录开发问题、解决过程、验证结果以及 AI 协作信息。

当前已完成阶段 2 的单表设计重置、阶段 3 的模型与迁移，以及阶段 4.1—4.2 的问题创建和列表接口。详情、更新和删除尚未开始。

## 当前能力

- `GET /health`：返回 `{"status": "ok"}`。
- `GET /docs`：打开 FastAPI 自动生成的 Swagger UI。
- `GET /openapi.json`：读取 OpenAPI 描述。
- 从环境配置读取 `mysql+asyncmy` 连接 URL，并隐藏密码展示。
- 每个数据库请求使用独立 `AsyncSession`；异常回滚，请求结束关闭。
- 应用关闭时释放异步 Engine，启动时不连接数据库、不创建表。
- 默认自动化测试不需要数据库，也不会读取 `.env`。
- 已定义唯一业务模型 `Issue`，包含 11 列、3 个状态和严格状态约束。
- 已配置 Alembic 异步环境和唯一初始 revision `20260828_01`；离线 SQL 和 `devfix_test` 真实升级均已验证与 `Issue` 模型一致。
- `POST /api/v1/issues`：校验输入并通过请求级 `AsyncSession` 创建问题，成功返回 201。
- `GET /api/v1/issues`：返回全部问题；按 `created_at DESC, id DESC` 稳定排序，空结果返回 `[]`。

## 已确认的 MVP 范围

- 只使用一张 `issues` 业务表。
- 实现 5 个业务接口：创建、列表、详情、部分更新和删除。
- 只创建 1 条 Alembic 初始迁移；`alembic_version` 是迁移工具元数据，不算业务表。
- 调用链保持为 Router → Schema → Service → AsyncSession → Model。
- 使用 Swagger UI 完成接口演示，不增加前端。
- 暂不实现多表关系、复杂事务、筛选、分页、搜索、统计、认证、LLM API、Redis、Docker 或部署。
- AI vibe coding 的证明来自范围调整、逐步实现、测试、代码理解、开发日志和 Git/PR 记录，不以接入大模型接口为目标。

## 环境要求

- Python 3.14
- MySQL 8.4（本机只读确认版本为 8.4.11，经典协议监听 3306）

项目当前使用的直接依赖已固定在 `requirements.txt`。异步 MySQL 驱动选择 `asyncmy`，数据库 URL 格式见 `.env.example`。

## 数据库配置

应用不提供默认数据库账号，也不会自动创建数据库或表。请使用专用的本地开发账号，不要使用 root；`.env` 已被 Git 忽略。

由你在本地创建 `.env` 并填写真实信息：

```powershell
Copy-Item .env.example .env
```

连接格式：

```text
mysql+asyncmy://用户名:经过URL编码的密码@127.0.0.1:3306/devfix?charset=utf8mb4
```

密码中的 `@`、`:`、`/`、`#` 等字符必须先进行 URL 编码。不要把真实连接串提交到 Git、写入文档或发送给 AI。

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

当前默认结果应为 `36 passed, 1 skipped`。真实 MySQL 用例默认需要显式启用，因此会被跳过；初次连接验收为 `1 passed in 0.27s`，迁移完成后的复验为 `1 passed in 0.11s`。

### 真实 MySQL 只读验收

先准备名称以 `_test` 结尾的专用测试数据库和最小权限账号，然后只在当前 PowerShell 会话中设置以下环境变量：

- `DEVFIX_RUN_MYSQL_TESTS=1`
- `DEVFIX_TEST_DATABASE_URL=<专用测试连接串>`

再执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error tests\integration\test_mysql_connection.py -rs
Remove-Item Env:DEVFIX_RUN_MYSQL_TESTS -ErrorAction SilentlyContinue
Remove-Item Env:DEVFIX_TEST_DATABASE_URL -ErrorAction SilentlyContinue
```

该测试只通过 `AsyncSession` 执行 `SELECT 1`，不会建表或写入数据。验收时必须显示 `1 passed`，不能以 skipped 代替。这个结果只能证明异步数据库连接成立；阶段 3 的迁移验收另外通过 `upgrade head`、`current --check-heads` 和 `alembic check` 完成。

## 当前目录

```text
alembic/
├── env.py
├── script.py.mako
└── versions/
    └── 20260828_01_create_issues_table.py
alembic.ini
app/
├── config.py
├── db.py
├── dependencies.py
├── enums.py
├── main.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   └── issue.py
├── routers/
│   ├── health.py
│   └── issues.py
├── schemas/
│   ├── health.py
│   └── issue.py
└── services/
    └── issue_service.py
docs/
├── ai-development-log.md
└── project-design.md
tests/
├── conftest.py
├── integration/
│   └── test_mysql_connection.py
├── test_config.py
├── test_database.py
├── test_issue_create.py
├── test_issue_list.py
├── test_migrations.py
├── test_models.py
└── test_health.py
```

Router 负责 HTTP 输入输出，Schema 负责请求和响应验证，Service 负责简单业务规则和显式提交，Model 负责 SQLAlchemy 映射。Session 依赖只管理异常回滚与关闭，不会隐式提交。`devfix_test` 当前已由 Alembic 创建 `issues` 和工具元数据表 `alembic_version`。

## 开发阶段

1. 阶段 0：需求与仓库初始化、`/health`（本地代码已完成）。
2. 阶段 1：异步 Engine、Session 工厂和数据库依赖（本地技术验收已完成）。
3. 阶段 2：将原三表方案重置为单表 CRUD，并确认 DevFix Lite v2.0 设计基线（已完成并提交）。
4. 阶段 3：实现一个 `Issue` 模型和一条 Alembic 初始迁移（代码、静态检查和真实测试库验收均已完成）。
5. 阶段 4：按创建、列表、详情、更新、删除五个小步完成 CRUD（创建和列表接口已完成无数据库测试）。
6. 阶段 5：使用自动化测试、真实 MySQL、Swagger、README、AI 开发日志和 Pull Request 完成验收。

下一步由开发者审阅并提交列表接口小步；随后实现 `GET /api/v1/issues/{issue_id}` 详情接口。

## 设计资料

- [DevFix Lite v2.0 项目设计基线](docs/project-design.md)
- [AI 开发日志](docs/ai-development-log.md)
