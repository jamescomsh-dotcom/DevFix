# DevFix

DevFix 是一个使用 FastAPI、SQLAlchemy AsyncSession、MySQL 和 Alembic 构建的异步后端项目，用于记录开发问题、AI 或人工解决方案、验证结果与最终有效解法。

当前完成 **阶段 1 的本地技术验收**：应用已经具备异步 Engine、Session 工厂、请求级 Session 依赖和关闭清理，专用测试账号下的真实 MySQL `SELECT 1` 已通过。

## 当前能力

- `GET /health`：返回 `{"status": "ok"}`。
- `GET /docs`：打开 FastAPI 自动生成的 Swagger UI。
- `GET /openapi.json`：读取 OpenAPI 描述。
- 从环境配置读取 `mysql+asyncmy` 连接 URL，并隐藏密码展示。
- 每个数据库请求使用独立 `AsyncSession`；异常回滚，请求结束关闭。
- 应用关闭时释放异步 Engine，启动时不连接数据库、不创建表。
- 默认自动化测试不需要数据库，也不会读取 `.env`。

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

默认结果应为 `16 passed, 1 skipped`。真实 MySQL 用例默认需要显式启用，因此会被跳过；本机已另行启用并取得 `1 passed` 的验收证据。

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

该测试只通过 `AsyncSession` 执行 `SELECT 1`，不会建表或写入数据。验收时必须显示 `1 passed`，不能以 skipped 代替。本机实际结果为 `1 passed in 0.27s`。

## 当前目录

```text
app/
├── config.py
├── db.py
├── dependencies.py
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
├── integration/
│   └── test_mysql_connection.py
├── test_config.py
├── test_database.py
└── test_health.py
```

Router 负责 HTTP 输入输出，Service 负责业务规则与事务，Model 负责 SQLAlchemy 映射，Schema 负责请求和响应验证。Session 依赖只管理回滚与关闭，不会隐式提交；后续 Service 将显式拥有写事务。当前仍没有业务模型或表。

## 开发阶段

1. 阶段 0：需求与仓库初始化、`/health`（本地代码已完成）。
2. 阶段 1：异步 Engine、Session 工厂和数据库依赖（本地技术验收已完成）。
3. 阶段 2：三张业务表及首条 Alembic 迁移。
4. 阶段 3：项目 CRUD。
5. 阶段 4：问题 CRUD。
6. 阶段 5：解决尝试与接受方案事务闭环。
7. 阶段 6：筛选、分页、搜索和统计。
8. 阶段 7：文档、演示和收尾。

阶段 1 已完成提交、推送和 Pull Request 审查；合并后进入阶段 2 的模型与 Alembic 初始迁移。

## 设计资料

- [项目设计基线](docs/project-design.md)
- [AI 开发日志](docs/ai-development-log.md)
