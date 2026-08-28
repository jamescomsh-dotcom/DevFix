# DevFix AI 开发日志

本日志记录 AI 参与、审查发现和实际验证证据。尚未由开发者完成的操作不会被写成已完成。

## 2026-08-27：阶段 0 本地项目初始化

### 原始需求

> 分析一下这个文件，然后开始进行项目。

输入资料为《DevFix_项目设计说明书_v1.0.md》。文档被当作需求资料解析，其中的示例提示词和 Git/GitHub 步骤没有被当作当前操作指令。

### 使用的 AI

Codex。

### 本轮范围

- 审查空仓库和现有 Python 环境。
- 提取 MVP 边界、业务规则、阶段计划、验收标准和设计歧义。
- 只实施设计中的阶段 0：项目骨架、`/health`、README、设计基线和测试。
- 不创建 Git 分支、commit、GitHub 仓库或 Pull Request。
- 不提前实现数据库连接、模型、迁移或业务 CRUD。

### 实施前发现

- 工作区只有无提交的 Git 仓库、空 `.gitignore` 和 Python 3.14.6 虚拟环境。
- 虚拟环境原先只有 pip。
- 通过 pip 的只解析检查确认，固定的 FastAPI、SQLAlchemy、Alembic、asyncmy 和测试依赖均有 Python 3.14 可安装版本。
- 原设计对并发接受方案、已解决问题重开、已接受方案结果降级等行为未完全定义，已记录为后续阶段决策，不在阶段 0 隐式处理。

### AI 首次实现的审查点

- 首次自动化测试得到 `3 passed`，但 Starlette 报告其 `TestClient + httpx` 适配路径已弃用，并建议迁移。
- 测试客户端因此改为异步 `HTTPX AsyncClient + ASGITransport`，使测试本身也走异步 ASGI 调用链；修改后全套测试在警告视为错误的模式下通过。
- 首次 README 使用 Uvicorn 默认端口 8000；独立审查确认本机 Windows 已排除 TCP 8000，实际启动会触发 `WinError 10013`。启动命令和访问地址已统一改为 8001。
- 独立依赖审查提示虚拟环境中的 pip 26.1.2 应升级；项目虚拟环境已更新到 pip 26.2.1。
- 本轮没有数据库，因此 `/health` 只表示应用进程可响应，不表示 MySQL 健康。

### 人工修改

尚未进行。开发者可在审查后补充。

### 最终验证

- `pip install -r requirements.txt`：成功，固定依赖均安装到 Python 3.14.6 虚拟环境。
- `pip check`：`No broken requirements found.`
- `python -m compileall -q app tests`：成功。
- `pytest -q -W error`：`3 passed`，没有警告。
- 按 README 使用 8001 实际启动 Uvicorn 后，`GET /health` 返回 200 和 `{"status":"ok"}`。
- 按 README 使用 8001 实际启动 Uvicorn 后，`GET /docs` 返回 200 和 HTML。
- `GET /openapi.json` 返回 200 且包含 `/health`。
- `netsh interface ipv4 show excludedportrange protocol=tcp` 确认本机排除端口为 8000；8001 启动探测通过。
- 探测结束后 Uvicorn 完成应用关闭流程。

以上只完成阶段 0 的本地代码与验证。Git 分支、commit、GitHub 仓库、Pull Request 和人工审查尚未完成。

### 当前可解释的请求链

```text
GET /health
  -> app.main 中的 FastAPI 应用
  -> app.routers.health.get_health()
  -> HealthResponse
  -> FastAPI 序列化为 {"status": "ok"}
```

## 2026-08-27：阶段 1 异步数据库连接

### 原始需求

> 进行下一阶段。

根据项目设计基线，本轮只进入阶段 1，不实现模型、Alembic 迁移、CRUD 或数据库健康接口。

### 使用的 AI

Codex。

### 实施前只读发现

- Windows 服务 `MySQL84` 正在运行且为自动启动。
- `mysql.exe` 与 `mysqld.exe` 版本均为 MySQL Community Server 8.4.11。
- MySQL 经典协议监听 3306，X Protocol 监听 33060。
- 两个 `mysqld` PID 是父子进程，不是两个独立实例。
- 没有读取 `.env`、`my.ini`、凭据或数据库数据，没有连接数据库，也没有改变服务状态。
- 专用开发账号、权限、`devfix` 与 `devfix_test` 数据库是否存在仍未确认。

### 本轮实现

- `Settings` 从 `.env` 加载可选 `DATABASE_URL`，使用 `SecretStr` 隐藏密码，并强制 `mysql+asyncmy`、用户名、主机和数据库名完整。
- `build_database_resources()` 只构造异步 Engine 和 `async_sessionmaker`；构造动作不会立即连接数据库。
- `get_database()` 为每个请求创建独立 `AsyncSession`，异常时回滚，结束时始终关闭，不自动 commit。
- FastAPI lifespan 在配置存在时准备资源，并在关闭时 `dispose()` Engine；配置缺失时 `/health` 仍可用。
- 增加显式启用的真实 MySQL 集成测试，只允许 `*_test` 数据库并执行只读 `SELECT 1`。
- 未调用 `create_all()`，未创建模型、表或迁移。

### 测试边界与审查

- 默认测试不读取 `.env`，不连接 MySQL。
- SQLAlchemy 2.0.52 的 `AsyncSession` 没有适合本测试直接断言的 `closed` 属性，因此通过 `AsyncMock` 精确验证 `rollback()` 和 `close()` 被 await。
- HTTPX `ASGITransport` 不自动驱动 lifespan；lifespan 使用 `application.router.lifespan_context()` 单独验证。
- 真实 MySQL 用例要求同时设置显式运行开关和专用测试连接串，避免误连普通开发库。
- 安全复核发现 Pydantic 校验错误默认可能展示连接串截断片段；已启用 `hide_input_in_errors` 并增加“不泄露原始连接值”的回归测试。
- 独立审查发现 `_env_file=None` 只禁用文件、不会禁用进程环境变量；“无配置”测试现已显式注入 `database_url=None`，并用污染环境回归证明测试隔离。
- 当前代码不会记录 `ValidationError.errors()`；未来若增加结构化错误日志，必须使用 `include_input=False`，避免把原始连接串写入日志。

### 当前验证

- `python -m compileall -q app tests`：成功。
- `pip check`：`No broken requirements found.`
- `pytest -q -W error -rs`：`16 passed, 1 skipped`。
- 默认套件中的跳过项是需要显式启用的真实 MySQL `SELECT 1`，不能单独作为连接成功证据。
- 搜索 `create_all`、同步 `Session` 等禁止模式：应用源码无匹配。
- 使用显式注入的空 Settings 启动 Uvicorn 8001（不读取 `.env`），`/health` 与 `/docs` 均返回 200，随后 lifespan 正常关闭。
- 2026-08-28，开发者创建空数据库 `devfix_test` 和账号 `devfix_test@127.0.0.1`，权限只授予 `devfix_test.*`。
- 开发者先用 MySQL 客户端通过 TCP 执行 `SELECT 1 AS connection_ok`，结果为 1。
- 开发者随后显式启用集成测试，通过 `asyncmy -> AsyncEngine -> AsyncSession -> MySQL` 执行 `SELECT 1`，结果为 `1 passed in 0.27s`。
- 密码没有发送给 AI；测试后已清理当前 PowerShell 中的连接串和运行开关环境变量。

### 人工操作与当前状态

1. 专用测试数据库、账号和限定授权：已完成。
2. 安全设置并清理临时测试连接变量：已完成。
3. 真实 MySQL 异步连接验收：已完成。
4. 阶段 1 本地技术验收：已完成。
5. 人工代码理解：开发者已确认完成。
6. Git/GitHub 写入由开发者执行，AI 未代为操作。

### 当前可解释的 Session 生命周期

```text
应用 lifespan 启动
  -> 读取 Settings
  -> 只构造 AsyncEngine 和 async_sessionmaker（尚不连接）
  -> 请求进入数据库路由
  -> get_database() 创建一个 AsyncSession
  -> Router 调用 Service
  -> Service 显式控制写事务
  -> 请求成功：依赖关闭 Session
  -> 请求异常：依赖 rollback 后关闭 Session
  -> 应用关闭：dispose Engine 连接池
```

## 2026-08-28：人工撤回三表方案并重置为单表 CRUD

### 开发者最新要求

> 基于现有项目和技术栈继续开发，将项目收敛为只涉及一张表的简单增删查改；完成后既能证明使用 AI vibe coding 协作，也能让开发者根据代码理解项目并积累 AI Web 开发经验。

### 审查结论

- 阶段 0 和阶段 1 的 FastAPI、异步 SQLAlchemy、MySQL 连接基础继续保留，现有默认测试基线为 `16 passed, 1 skipped`。
- 当前仓库没有业务模型、业务表或 Alembic 迁移，适合在现有基础上重新确定最小业务范围。
- 原三表方案超出本次学习型 MVP 的必要范围，会引入外键、多表事务和额外接口。
- 此前生成但未提交的阶段 2 模型内容已按开发者要求撤回，撤回后原有测试仍通过。
- 仓库外的 v1.0 说明书保留为历史参考；仓库内 `docs/project-design.md` 作为当前 v2.0 实施基线。

### 已确认的 v2.0 范围

- 只实现一张 `issues` 业务表。
- 只实现创建、列表、详情、部分更新和删除 5 个业务接口。
- 只创建 1 条 Alembic 初始迁移；迁移工具自己的 `alembic_version` 不属于业务表。
- `ai_tool`、`ai_prompt` 等字段只用于记录 AI 协作过程，不接入 LLM API。
- 不实现多表关系、复杂事务、搜索、筛选、分页、统计、认证、前端、Redis、Docker 或部署。
- 本轮只同步设计文档、README 和开发日志，不创建模型、迁移或 CRUD 代码。

### AI 协作证据

- 开发者主动审查项目复杂度，并决定撤回不符合学习目标的三表方案。
- AI 只撤回了未提交的阶段 2 内容，保留已验收的数据库基础，并重新运行测试确认没有破坏现有能力。
- AI 先分析仓库与历史设计，给出单表方案；开发者确认后才写入当前设计基线。
- 数据库初始化、真实验收和所有 Git/GitHub 写入仍由开发者掌控。
- 下一道人工确认门：开发者审阅并提交本轮文档，再进入 `Issue` 模型与初始迁移的 Red → Green 小步实现。
