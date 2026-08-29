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

## 2026-08-28：阶段 3.1 单个 Issue 模型

### 本轮边界

- 只实现 `IssueStatus`、`Base`、`Issue` 和纯 SQLAlchemy metadata 测试。
- 不配置 Alembic，不创建数据库表，不连接 MySQL。
- 不实现 Schema、Router、Service 或 CRUD。

### 第一次 Red → Green

1. 先添加 `tests/test_models.py`，测试因 `app.enums` 不存在而在收集阶段失败。
2. 实现一个共享状态枚举、一个 Declarative Base 和唯一的 `Issue` 模型。
3. 模型测试达到 `6 passed`。

模型严格对应设计中的 11 列，不包含外键、relationship、第二张表或额外索引。`status` 使用非原生 SQLAlchemy Enum，因此 MySQL 列仍是 `VARCHAR(20)`；ORM 默认值和数据库默认值均为 `OPEN`。时间使用约定为 UTC 的无时区值写入 `DATETIME(6)`。

### 独立审查与第二次 Red → Green

独立审查发现：MySQL 常用的大小写不敏感排序规则可能让自动状态 `CHECK` 接受原生 SQL 写入的 `open`，但 SQLAlchemy 读取时无法把它转换为合法枚举。

1. 先增加 MySQL 方言 DDL 测试，当前实现出现 `2 failed, 5 passed`。
2. 关闭 Enum 自动约束，改为命名的严格检查：`CAST(status AS BINARY) IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')`。
3. 同时让测试实际执行时间默认回调，并避免把“无索引”锁成永久契约。
4. 修正后模型测试达到 `7 passed`。

这次修正证明 AI 生成代码仍需要独立审查和可复现测试，不能只看到第一次 Green 就结束。

### 当前验证

- `pytest -q -W error -rs`：`23 passed, 1 skipped`。
- `python -m compileall -q app tests`：成功。
- `pip check`：`No broken requirements found.`
- SQLAlchemy mapper 配置与 MySQL 8 方言 DDL 静态编译成功。
- 生成的 DDL 只有一张 `issues` 业务表、11 列、主键和严格状态约束。
- 跳过项仍是显式启用的真实 MySQL `SELECT 1`；本轮没有读取 `.env` 或访问数据库。
- AI 未执行 commit、push、PR、迁移或数据库写入。

## 2026-08-28：阶段 3.2 Alembic 初始迁移定义

### 本轮边界

- 配置 Alembic 异步环境并创建唯一初始 revision。
- 通过静态 metadata 和离线 SQL 检查迁移，不连接真实数据库。
- 不实现 Schema、Router、Service 或 CRUD。
- `upgrade/current/check` 的真实 MySQL 验收继续由开发者在 `devfix_test` 上执行。

### Red → Green

1. 先添加 `tests/test_migrations.py`，因为 `alembic.ini` 和迁移目录不存在，得到 `3 failed`。
2. 创建 `alembic.ini`、异步 `env.py`、官方结构的 revision 模板和初始迁移。
3. 测试验证只有一个 base/head、迁移 SQL 与 `Issue` 模型 SQL 完全一致、downgrade 只删除 `issues`，达到 `3 passed`。

### 安全审查修正

独立审查指出：不应把原始数据库 URL 临时放入 Alembic 配置字典，否则 URL 编码中的 `%` 可能触发 ConfigParser 插值问题，也会扩大秘密在配置对象中的停留范围。

1. 先把“`alembic.ini` 不含 `sqlalchemy.url`、使用 `make_url()` 和 `create_async_engine()`”写进测试，得到 `1 failed, 2 passed`。
2. `env.py` 改为从现有 `Settings` 获取 `SecretStr`，转换成 SQLAlchemy `URL` 对象，并直接创建短生命周期异步 Engine。
3. 修正后迁移测试恢复为 `3 passed`。

### 当前静态验证

- `alembic heads`：`20260828_01 (head)`。
- `alembic history --verbose`：唯一 revision，父节点为 `<base>`。
- 使用假的端口 1 连接串执行 `upgrade head --sql` 成功；命令只渲染 SQL，没有创建 Engine 或连接数据库。
- 离线 SQL 由 Alembic 管理 `alembic_version`，唯一业务 DDL 是创建 `issues`。
- `pytest -q -W error -rs`：`26 passed, 1 skipped`。
- `python -m compileall -q app tests alembic`：成功。
- `git diff --check`：通过。
- 没有读取项目 `.env`，没有执行真实迁移、数据库写入或 Git 写入。

### 开发者真实 MySQL 验收

开发者提交 Alembic 小步后，在同一个 PowerShell 会话中通过 `Read-Host` 临时设置专用测试连接串。连接串和密码没有发送给 AI，也没有写入 Git。

验收顺序与结果：

1. 只打印 URL 中的数据库名称，确认目标严格为 `devfix_test`。
2. `alembic upgrade head`：成功执行 `upgrade -> 20260828_01`，创建迁移管理表和唯一业务表。
3. `alembic current --check-heads`：输出 `20260828_01 (head)`。
4. `alembic check`：输出 `No new upgrade operations detected.`，证明数据库结构与当前模型一致。
5. 显式启用异步 MySQL 集成测试：`1 passed in 0.11s`。
6. 删除 `DATABASE_URL`、`DEVFIX_TEST_DATABASE_URL` 和 `DEVFIX_RUN_MYSQL_TESTS` 三个临时环境变量；验证命令无输出。

MySQL 提示 `Will assume non-transactional DDL` 属于正常行为，也说明真实迁移必须先在专用测试库验收，不能假设失败时整次 DDL 会自动回滚。

阶段 3 至此完成。AI 负责配置、迁移定义、测试、审查和指导；开发者保留数据库凭据并亲自执行真实迁移与验收。

## 2026-08-28：阶段 4.1 创建 Issue 接口

### 本轮边界

- 只实现 `POST /api/v1/issues`。
- 只增加 `IssueCreate`、`IssueRead`、一个创建 Service 和一个 POST Router。
- 不实现 GET、PATCH、DELETE、`IssueUpdate`、搜索、分页或异常框架。
- 默认测试通过 FastAPI dependency override 使用假的 Session，不读取 `.env`、不连接 MySQL。

### Red → Green

1. 先添加创建接口测试，因为 `app.schemas.issue` 不存在，测试在收集阶段 Red。
2. `IssueCreate` 对 title、description 和 ai_tool 去除首尾空格并限制长度，使用 `extra='forbid'` 拒绝 status、id 和未知字段。
3. Service 严格按 `add -> flush -> commit` 写入；异常不被吞掉，由现有数据库依赖负责 rollback 和 close。
4. Router 返回 201，并通过 `IssueRead(from_attributes=True)` 输出完整 11 个字段。
5. OpenAPI 测试锁定 `/api/v1/issues` 当前只有 POST，且尚不存在 `/{issue_id}`。
6. 目标测试达到 `7 passed`。

### 独立审查修正

审查确认当前所有响应字段在 flush 后已经确定，且 Session 使用 `expire_on_commit=False`，因此不需要为了创建响应额外执行 refresh SELECT。项目设计同步改为：只有数据库生成了额外响应值时才 refresh。

测试还增加共享事件列表，明确锁定调用顺序必须为：

```text
add
  -> flush
  -> commit
```

### 当前验证

- `pytest -q tests/test_issue_create.py -W error`：`7 passed`。
- `pytest -q -W error -rs`：`33 passed, 1 skipped`。
- OpenAPI 静态检查：`POST_ONLY_OK`。
- `python -m compileall -q app tests`：成功。
- `git diff --check`：通过。
- 本轮没有连接数据库，不能把 fake Session 测试称为真实 MySQL 创建验收。

## 2026-08-28：阶段 4.2 查询 Issue 列表接口

### 本轮边界

- 只实现 `GET /api/v1/issues`，复用已有 `IssueRead` 和数据库依赖。
- 不增加筛选、搜索、分页、统计、详情路由或新 Schema。
- 不修改模型、迁移和数据库配置，不读取 `.env`，不连接 MySQL。

### Red → Green

1. 先增加列表、空列表和 OpenAPI 测试；实现前两个请求返回 405，OpenAPI 也缺少 GET，得到 `3 failed`。
2. Service 使用 `select(Issue)`，把 `created_at DESC, id DESC` 排序交给数据库执行。
3. `await session.scalars(statement)` 后同步调用 `result.all()`，转换为 `list[Issue]` 返回。
4. Router 在原 collection path 增加 GET，使用 `response_model=list[IssueRead]`；有数据返回数组，无数据返回 `[]`。
5. 阶段 4.1 的 OpenAPI 测试同步收窄为只验证 POST 创建契约；新增测试负责锁定 collection path 的完整方法集合为 GET 和 POST。

### 只读边界与测试证据

- 测试编译传给 `session.scalars()` 的 MySQL SQL，精确验证排序为 `issues.created_at DESC, issues.id DESC`，而不是依赖假数据碰巧排好序。
- 测试验证查询不包含 WHERE、LIMIT 或 OFFSET，符合当前无筛选、无分页范围。
- 假 Session 明确验证 GET 不调用 `add`、`flush`、`commit`、`refresh` 或 `delete`。
- 定向测试：`10 passed`（创建与列表接口）。
- 完整默认测试：`36 passed, 1 skipped`；跳过项仍是真实 MySQL 连接用例。
- `git diff --check`：通过。

本轮只能证明 FastAPI 调用链、响应序列化、SQL 结构和只读行为通过无数据库自动化测试，尚未进行真实 MySQL 列表查询或 Swagger 人工验收。

### 当前可解释的列表调用链

```text
GET /api/v1/issues
  -> FastAPI 注入请求级 AsyncSession
  -> issues Router 调用 list_issues Service
  -> Service 构造 SELECT ... ORDER BY created_at DESC, id DESC
  -> AsyncSession.scalars() 获取 Issue 标量结果
  -> IssueRead 将 ORM 对象列表序列化为 JSON 数组
  -> 数据库依赖关闭 Session
```

## 2026-08-28：阶段 4.3 查询单个 Issue 详情接口

### 本轮边界

- 只实现 `GET /api/v1/issues/{issue_id}`，复用已有 `IssueRead`。
- 找到记录返回 200，找不到返回 404，非整数路径参数由 FastAPI 返回 422。
- 不增加新 Schema、筛选、关系、PATCH 或 DELETE，也不修改模型和迁移。
- 默认测试继续使用 dependency override，不读取 `.env`，不连接 MySQL。

### Red → Green

1. 先增加存在记录、不存在记录、非整数参数和 OpenAPI 四个测试；实现前得到 `4 failed`。
2. Service 使用 `await session.get(Issue, issue_id)` 表达纯主键查询，返回 `Issue | None`。
3. Router 把 Service 返回的 `None` 转换为 404 和 `{"detail": "Issue 不存在。"}`，找到时交给 `IssueRead` 输出完整 11 个字段。
4. OpenAPI 明确详情路径只有 GET，同时声明 200、404 和自动生成的 422 响应。
5. 创建和列表测试删除已经过期的“详情路径不存在”断言；详情测试接管 item path 的完整边界。

### 只读边界与测试证据

- 测试精确验证 `session.get(Issue, issue_id)` 只调用一次，并验证不存在时仍查询目标主键。
- 测试验证详情 GET 不调用 `add`、`flush`、`commit`、`refresh` 或 `delete`。
- 非整数路径参数在进入 Service 前返回 422，假 Session 的 `get()` 未被调用。
- 定向测试：`14 passed`（创建、列表与详情接口）。
- 完整默认测试：`40 passed, 1 skipped`；跳过项仍是真实 MySQL 连接用例。
- `python -m compileall -q app tests alembic`：成功。
- `git diff --check`：通过。

`AsyncSession.get()` 可能先命中当前 Session 的 identity map，因此无数据库测试验证的是主键查询调用契约，而不是宣称检查了实际 MySQL SQL。本轮尚未进行真实 MySQL 详情查询或 Swagger 人工验收。

### 当前可解释的详情调用链

```text
GET /api/v1/issues/{issue_id}
  -> FastAPI 把路径参数校验为 int，并注入请求级 AsyncSession
  -> issues Router 调用 get_issue Service
  -> Service 使用 AsyncSession.get(Issue, issue_id) 按主键查询
  -> 找到：IssueRead 将 ORM 对象序列化为完整 JSON
  -> 未找到：Router 返回 404
  -> 数据库依赖关闭 Session
```

## 2026-08-29：阶段 4.4 部分更新 Issue 接口

### 本轮边界

- 只实现 `PATCH /api/v1/issues/{issue_id}` 和设计中最后一个请求 Schema `IssueUpdate`。
- 只允许修改 title、description、error_message、ai_tool、ai_prompt、solution、verification_notes 和 status。
- 不允许修改 id、created_at、updated_at 或未知字段，不增加状态机、并发控制、PUT 或 DELETE。
- 默认测试继续使用 dependency override，不读取 `.env`，不连接 MySQL。

### PATCH 字段语义

- 字段未提供：不修改原值。
- error_message、ai_tool、ai_prompt、solution、verification_notes 明确传 `null`：清空字段。
- title、description、status 明确传 `null`：返回 422。
- 空对象 `{}`、空白必填文本、非法状态、超长 ai_tool 和服务端字段：返回 422。
- Service 必须使用 `model_dump(exclude_unset=True)`；不能使用 `exclude_none=True`，否则无法区分“未提供”和“明确清空”。

### Red → Green

1. 先增加部分更新、非法输入、404、flush 异常和 OpenAPI 测试；实现前 11 个用例全部因 PATCH 返回 405 或 OpenAPI 缺少 PATCH 而失败。
2. `IssueUpdate` 使用 `extra='forbid'`，复用创建接口的去空格和长度规则，并通过 `model_fields_set` 拒绝空 PATCH 与非空字段的 null。
3. Service 按 `get -> setattr 明确提供的字段 -> flush -> commit` 更新，不重新 add，也不 refresh。
4. Router 返回完整 `IssueRead`；Service 返回 `None` 时转换为固定 404。
5. 详情 OpenAPI 测试收窄为验证 GET 自身契约；更新测试接管 item path 当前恰好只有 GET 和 PATCH 的边界。

### 测试与审查证据

- 成功测试同时更新 title、ai_tool、status，并用 `solution: null` 证明可空字段能够清空；未提供的 description 等字段保持原值。
- 共享事件列表锁定调用顺序为 `get -> flush -> commit`，同时确认没有 add、refresh 或 delete。
- 找不到记录时返回 404，且不 flush、不 commit；flush 抛错时也不会 commit，异常继续交给数据库依赖 rollback。
- 更新接口定向测试：`11 passed`。
- 创建、列表、详情和更新接口测试：`25 passed`。
- 完整默认测试：`51 passed, 1 skipped`；跳过项仍是真实 MySQL 连接用例。
- `python -m compileall -q app tests alembic`：成功。
- `git diff --check`：通过。

`updated_at` 继续由 SQLAlchemy 模型的 Python `onupdate` 在实际 UPDATE 的 flush 阶段生成，模型测试已独立验证该回调。如果客户端提交的值与原值完全相同，SQLAlchemy 可能不发送 UPDATE，此时时间不变化；当前简单 MVP 接受这一语义。

本轮证明的是 Schema 验证、部分字段映射、事务调用顺序、HTTP 响应和 OpenAPI 契约；尚未进行真实 MySQL 更新或 Swagger 人工验收。

### 当前可解释的更新调用链

```text
PATCH /api/v1/issues/{issue_id}
  -> FastAPI 使用 IssueUpdate 校验请求体
  -> Router 调用 update_issue Service
  -> Service 使用 AsyncSession.get() 查询记录
  -> 只 setattr model_dump(exclude_unset=True) 中的字段
  -> flush 发送 UPDATE，并在真实变更时生成 updated_at
  -> commit 提交单表事务
  -> IssueRead 序列化完整响应
  -> 数据库依赖关闭 Session；异常时先 rollback
```

## 2026-08-29：阶段 4.5 删除 Issue 接口

### 本轮边界

- 只实现 `DELETE /api/v1/issues/{issue_id}` 硬删除。
- 成功返回严格无响应体的 204；记录不存在返回固定 404；非整数路径参数返回 422。
- 不实现软删除、批量删除、确认请求体、删除原因、级联关系或删除前数据响应。
- 不修改 Schema、Model、Migration、数据库配置或其他四个业务接口。
- 默认测试继续使用 dependency override，不读取 `.env`，不连接 MySQL。

### Red → Green

1. 先增加成功删除、删除后查询、不存在、非整数参数、delete/flush 异常和 OpenAPI 测试；实现前 6 个用例全部因 DELETE 返回 405 或 OpenAPI 缺少 DELETE 而失败。
2. Service 按 `get -> await delete -> flush -> commit` 执行；不存在时返回 False，异常不被吞掉。
3. 显式 flush 使 DELETE 数据库错误发生在 commit 之前；delete 或 flush 失败时均不 commit，生产数据库依赖负责 rollback。
4. Router 把 False 转换为 404；成功时显式返回 `Response(status_code=204)`，确保没有 `null`、JSON 对象或 Content-Type。
5. 更新接口的 OpenAPI 测试收窄为验证 PATCH 自身；删除测试接管 item path 当前完整方法集合 GET、PATCH、DELETE。

### 测试与审查证据

- 成功测试精确验证 204、空字节响应体、空文本和无 Content-Type。
- 共享事件列表锁定 `get -> delete -> flush -> commit`，并验证 `AsyncSession.delete()` 被正确 await。
- fake 状态只在 commit 成功后切换为已删除，随后 GET 同一 ID 返回 404；这验证调用链，不冒充真实数据库持久化。
- 不存在时不调用 delete、flush、commit；非整数 ID 在进入 Service 前返回 422。
- delete 失败时不 flush、不 commit；flush 失败时不 commit。
- 删除接口定向测试：`6 passed`。
- 五个 CRUD 接口测试：`31 passed`。
- 完整默认测试：`57 passed, 1 skipped`；跳过项仍是真实 MySQL 连接用例。
- `python -m compileall -q app tests alembic`：成功。
- `git diff --check`：通过。

本轮完成了阶段 4 的五个接口代码和无数据库测试，但尚未证明 MySQL 中记录真实删除，也尚未完成 Swagger 人工演示；这些属于阶段 5 验收。

### 当前可解释的删除调用链

```text
DELETE /api/v1/issues/{issue_id}
  -> FastAPI 校验 issue_id 并注入请求级 AsyncSession
  -> Router 调用 delete_issue Service
  -> Service 使用 AsyncSession.get() 查询记录
  -> 不存在：Router 返回 404
  -> 存在：await delete 标记删除，flush 发送 DELETE，commit 提交
  -> Router 返回严格空响应体的 204
  -> 数据库依赖关闭 Session；异常时先 rollback
```
