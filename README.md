# DevFix

DevFix Lite 是一个使用 FastAPI、SQLAlchemy AsyncSession、MySQL 和 Alembic 构建的单表异步 CRUD 后端，用于记录开发问题、解决过程、验证结果以及 AI 协作信息。

当前已完成阶段 2 的单表设计重置、阶段 3 的模型与迁移，以及阶段 4.1—4.5 的创建、列表、详情、部分更新和删除接口。五个接口已通过无数据库自动化测试，并已在专用 `devfix_test` 完成真实 HTTP CRUD 自动化验收和 Swagger 人工验收。

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
- `GET /api/v1/issues/{issue_id}`：按主键返回完整问题记录；不存在返回 404，非整数路径参数返回 422。
- `PATCH /api/v1/issues/{issue_id}`：只更新请求中明确提供的字段；支持清空可空字段，空请求或非法输入返回 422，不存在返回 404。
- `DELETE /api/v1/issues/{issue_id}`：硬删除一条问题记录；成功返回无响应体的 204，不存在返回 404。

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

当前默认结果应为 `57 passed, 2 skipped`。两个真实 MySQL 用例使用不同的显式开关，默认均会跳过：一个只验证 `SELECT 1`，另一个执行完整 HTTP CRUD。初次连接验收为 `1 passed in 0.27s`，迁移完成后的复验为 `1 passed in 0.11s`。

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

### 真实 MySQL CRUD 验收

前提是 `devfix_test` 已通过 Alembic 升级到 head。该测试会真实写入、查询、修改和删除数据，因此使用独立开关，不会被上面的只读开关意外启用。

只在当前 PowerShell 会话中设置：

- `DEVFIX_RUN_MYSQL_CRUD_TESTS=1`
- `DEVFIX_TEST_DATABASE_URL=<专用测试连接串>`

然后执行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error tests\integration\test_mysql_crud.py -rs
Remove-Item Env:DEVFIX_RUN_MYSQL_CRUD_TESTS -ErrorAction SilentlyContinue
Remove-Item Env:DEVFIX_TEST_DATABASE_URL -ErrorAction SilentlyContinue
```

测试只允许数据库名以 `_test` 结尾，通过真实 HTTP 请求依次执行 POST、列表、详情、PATCH、DELETE 和删除后 404。每次使用唯一 UUID title 和 marker 标记自己的记录，并在 `finally` 中只清理匹配任一标记的数据；不会建表、迁移、清空表或删除其他记录。2026-08-29，开发者在 `devfix_test` 显式运行该测试，结果为 `1 passed in 0.13s`，随后清理了连接串、运行开关和安全字符串变量。

### Swagger 人工验收

2026-08-29，开发者在当前 PowerShell 会话中临时设置指向 `devfix_test` 的 `DATABASE_URL`，使用 8001 端口启动 Uvicorn，并在 `/docs` 依次完成以下验证：

- POST 返回 201，创建 ID 为 2、状态为 `OPEN` 的记录。
- 列表 GET 返回 200，并包含新记录；详情 GET 返回 200。
- PATCH 返回 200，将 `error_message` 清空，把 `status` 改为 `RESOLVED`，同时写入解决方案和验证说明；未提交的标题与描述保持不变，`updated_at` 发生变化。
- 执行 DELETE 后再次 GET，返回 404 和 `{"detail": "Issue 不存在。"}`，证明记录已从真实 MySQL 删除。

严格空响应体的 DELETE 204 契约由自动化测试覆盖；人工截图明确记录了删除后的 404 结果。验收结束后，开发者停止 Uvicorn，并清理了临时 `DATABASE_URL` 和安全字符串变量；连接串与密码未写入文件或发送给 AI。

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
│   ├── test_mysql_connection.py
│   └── test_mysql_crud.py
├── test_config.py
├── test_database.py
├── test_issue_create.py
├── test_issue_delete.py
├── test_issue_detail.py
├── test_issue_list.py
├── test_issue_update.py
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
5. 阶段 4：按创建、列表、详情、更新、删除五个小步完成 CRUD（五个接口均已完成无数据库测试）。
6. 阶段 5：使用自动化测试、真实 MySQL、Swagger、README、AI 开发日志和 Pull Request 完成验收（真实 CRUD 自动化验收与 Swagger 人工验收已通过，PR 收尾待完成）。

下一步由开发者审阅并提交阶段 5 验收改动，然后完成 GitHub Pull Request 收尾。

## 设计资料

- [DevFix Lite v2.0 项目设计基线](docs/project-design.md)
- [AI 开发日志](docs/ai-development-log.md)
