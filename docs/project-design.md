# DevFix Lite 项目设计基线 v2.0

本文档是 DevFix 当前仓库的唯一实施基线。外部的《DevFix_项目设计说明书_v1.0.md》保留为历史设计，不作为当前代码范围。

v1.0 原计划使用 projects、issues 和 solution_attempts 三张业务表，并包含多方案接受事务、级联关系、搜索和统计。开发者审查后认为它超过了当前学习目标，已要求撤回未提交的三表模型实现，并确认将项目缩小为单表异步 CRUD。

原说明书中的提示词、GitHub 流程和人工清单只作为参考，不自动授权任何文件、Git、数据库或外部平台写入。

## 1. 项目目标

DevFix Lite 是一个个人开发问题记录 API，用于保存：

- 遇到的开发问题和原始报错。
- 使用过的 AI 工具和核心提示词。
- 当前或最终解决方案。
- 人工验证过程与结果。
- 问题当前状态。

项目完成后，开发者应能通过 Swagger 演示完整 CRUD，并能解释请求如何经过 Router、Schema、Service、AsyncSession、Model 到达 MySQL。

AI 不作为产品内置功能。项目不会调用任何大模型 API；AI Vibe Coding 的证明来自需求拆分、测试、审查、人工理解、Git 和 Pull Request 记录。

## 2. MVP 硬边界

本次 MVP 固定为：

- 一个用户。
- 一个 issues 业务表。
- 五个业务 CRUD 接口。
- 一条初始 Alembic 迁移。
- Swagger UI 作为唯一操作界面。
- SQLAlchemy 全异步数据库访问。
- 约十个关键行为测试及少量真实 MySQL 验收。

明确不做：

- projects、solution_attempts 或其他业务表。
- 外键和多表关系。
- 多候选方案、最终方案接受事务和并发锁。
- 搜索、筛选、统计、标签、软删除和复杂分页。
- 登录、权限、多用户、前端和文件上传。
- Redis、消息队列、后台任务和 WebSocket。
- LLM API、Docker、部署和云服务。
- Repository 层、通用 CRUD 基类和复杂异常框架。

Alembic 会自动创建 alembic_version，它是迁移元数据表，不算第二张业务表。

## 3. 技术栈

- Python 3.14
- FastAPI
- MySQL 8.4
- SQLAlchemy 2.x AsyncSession
- asyncmy
- Alembic
- Pydantic 2
- pytest、pytest-asyncio 和 HTTPX
- Git 与 GitHub Pull Request

不增加新的运行时技术或依赖。

## 4. 现有基础

阶段 0 和阶段 1 已完成并保留：

- FastAPI 应用工厂、Swagger、OpenAPI 和 GET /health。
- 从环境读取 mysql+asyncmy 连接 URL。
- 使用 SecretStr 隐藏数据库密码。
- 异步 Engine 和 async_sessionmaker。
- 每个请求独立使用一个 AsyncSession。
- 请求异常时回滚，请求结束时关闭 Session。
- 应用关闭时释放 Engine。
- FastAPI 启动不连接数据库、不创建表。
- 默认测试不读取 .env，也不连接 MySQL。
- 专用 devfix_test 数据库的真实 SELECT 1 已通过。

当前尚未创建任何业务模型、业务表、Alembic 环境或 CRUD 接口，因此本次范围调整不需要迁移旧业务数据。

## 5. 唯一业务对象

每条 Issue 记录对应一个完整的开发问题记录：

~~~text
开发问题
  -> 可选的 AI 工具与提示词
  -> 可选的解决方案
  -> 可选的人工验证说明
  -> 当前状态
~~~

第一版不保存同一个问题的多个历史方案。后续即使需要扩展，也不能在本 MVP 中增加第二张表或使用 JSON 数组模拟多表结构。

## 6. issues 表

| 字段 | MySQL 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGINT | 主键、自增 | 记录 ID |
| title | VARCHAR(200) | 非空 | 问题标题 |
| description | TEXT | 非空 | 问题背景与现象 |
| error_message | TEXT | 可空 | 原始报错 |
| ai_tool | VARCHAR(50) | 可空 | 例如 Codex、ChatGPT |
| ai_prompt | TEXT | 可空 | 使用过的核心提示词 |
| solution | TEXT | 可空 | 当前或最终解决方案 |
| verification_notes | TEXT | 可空 | 人工验证过程与结果 |
| status | VARCHAR(20) | 非空、默认 OPEN | 问题状态 |
| created_at | DATETIME(6) | 非空 | UTC 创建时间 |
| updated_at | DATETIME(6) | 非空 | UTC 修改时间 |

标题不设置唯一约束，因为相似问题可能重复出现。

ai_prompt 禁止保存密码、访问令牌、数据库连接串或其他秘密。

## 7. 状态规则

状态只允许：

~~~text
OPEN
IN_PROGRESS
RESOLVED
~~~

规则保持简单：

1. POST 创建接口不接收 status，新记录一律为 OPEN。
2. 普通 PATCH 可以直接修改为任何合法状态。
3. 不设计自动状态转换。
4. 不要求 RESOLVED 必须同时存在 solution。
5. 不设计重开限制、接受方案事务或并发控制。

## 8. API 范围

业务接口统一使用 /api/v1 前缀。

| 方法 | 路径 | 状态码 | 说明 |
|---|---|---|---|
| POST | /api/v1/issues | 201 | 创建问题记录 |
| GET | /api/v1/issues | 200 | 查询全部记录 |
| GET | /api/v1/issues/{issue_id} | 200 / 404 | 查询一条记录 |
| PATCH | /api/v1/issues/{issue_id} | 200 / 404 / 422 | 部分修改 |
| DELETE | /api/v1/issues/{issue_id} | 204 / 404 | 删除记录 |

系统接口继续保留：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 只检查 FastAPI 进程能否响应 |
| GET | /docs | Swagger UI |
| GET | /openapi.json | OpenAPI 描述 |

GET /api/v1/issues 第一版不接收搜索、筛选或分页参数，只按 created_at 倒序、id 倒序返回。

## 9. Schema 范围

只创建三个 Pydantic 模型：

- IssueCreate：title、description 必填，其余记录字段可选；不接收 status。
- IssueUpdate：PATCH 输入，可编辑字段均可选并包含 status，但至少提供一个。
- IssueRead：统一响应。

输入规则：

- title 去除首尾空格后长度为 1 到 200。
- description 去除首尾空格后不能为空。
- ai_tool 若提供，去除首尾空格后最长 50。
- status 只允许在 PATCH 中提供，并且只能使用三个允许值。
- PATCH 至少包含一个明确提供的字段。
- id、created_at 和 updated_at 不能由客户端填写。

## 10. 代码分层

继续使用现有的小型分层，不增加 Repository：

~~~text
Swagger / HTTP
  -> app/routers/issues.py
  -> Pydantic Issue Schema
  -> app/services/issue_service.py
  -> AsyncSession
  -> app/models/issue.py
  -> MySQL issues
  -> IssueRead
~~~

职责：

- Router：HTTP 参数、响应模型、状态码和 404 转换。
- Schema：输入验证和响应边界。
- Service：查询、写入、flush、commit；只有数据库生成了额外响应值时才 refresh。
- Model：issues 表映射。
- Dependency：创建 Session、异常回滚并始终关闭。

写操作由 Service 显式 commit。数据库依赖不会隐式提交。
这里的事务边界只指单次写操作的 commit、异常 rollback 和 Session 关闭，不包含多表事务。

## 11. 数据库与迁移

必须使用 Alembic：

1. 配置 Base.metadata 为 target_metadata。
2. 生成一条创建 issues 的初始迁移。
3. 人工检查迁移只包含预期的 create_table 和约束。
4. 在空的 devfix_test 数据库执行 upgrade head。
5. 验证 current 与 heads 指向同一 revision。
6. 执行 alembic check，确认模型和数据库没有待生成差异。

禁止：

- 在应用启动时调用 Base.metadata.create_all。
- 把真实数据库 URL 写进 alembic.ini。
- 让 AI 读取、输出或保存数据库密码。
- 在非测试数据库运行破坏性验收操作。

## 12. 错误规则

| 场景 | 状态码 |
|---|---|
| 创建成功 | 201 |
| 查询或修改成功 | 200 |
| 删除成功 | 204 |
| 输入校验失败 | 422 |
| Issue 不存在 | 404 |

本 MVP 不需要 409 冲突响应，也不设计复杂错误码体系。

## 13. 关键测试

现有阶段 0、1 测试必须继续通过。在此基础上至少验证：

1. 合法创建返回 201，缺省状态为 OPEN。
2. 空白 title 或 description 返回 422。
3. 列表能够返回已创建记录，并保持稳定倒序。
4. 查询存在记录返回 200。
5. 查询不存在记录返回 404。
6. PATCH 只修改客户端提供的字段。
7. 非法 status 返回 422。
8. 空 PATCH 返回 422。
9. 删除返回 204，响应体为空，随后查询返回 404。
10. 删除不存在记录返回 404。

测试分为：

- 默认自动化测试：不读取 .env，不依赖真实 MySQL。
- 显式启用的 MySQL 验收：只连接名称以 _test 结尾的数据库，验证迁移和一轮真实 CRUD。
- Swagger 人工验收：开发者亲自完成创建、查询、修改和删除。

不能用 Mock 测试代替真实 MySQL 验收，也不能把 SELECT 1 称为 CRUD 已验证。

## 14. 分阶段实施

### 阶段 0：仓库和健康接口

状态：已完成并合并。

### 阶段 1：异步数据库基础设施

状态：已完成、真实连接已验收并合并。

### 阶段 2：设计范围重置

交付：

- 将三表设计改为单表 CRUD。
- 更新 README。
- 在 AI 开发日志记录人工撤回和范围缩减。

验收：

- 文档中没有仍被声明为当前计划的多表、复杂事务、搜索或统计。
- 不创建任何业务代码。

### 阶段 3：单模型和初始迁移

交付：

- IssueStatus。
- Base 和 Issue 模型。
- Alembic 环境。
- 一条初始迁移。

验收：

- 空 devfix_test 能 upgrade head。
- 数据库只有 issues 和 alembic_version 两张项目相关表。
- current、heads 和模型结构一致。
- FastAPI 启动不自动建表。

### 阶段 4：五个 CRUD 接口

按以下顺序逐小步实现：

1. POST 创建。
2. GET 列表。
3. GET 详情。
4. PATCH 修改。
5. DELETE 删除。

每一步都要求先出现可解释的失败测试，再实现到测试通过。

### 阶段 5：验收和展示

交付：

- 完整自动化测试。
- 真实 MySQL CRUD 验收。
- Swagger 演示。
- README 使用示例。
- AI 开发日志和人工理解记录。
- GitHub Pull Request 自我审查。

## 15. AI Vibe Coding 证据

项目完成后必须留下以下证据：

- 开发者主动把过度复杂的三表设计缩为单表。
- AI 修改前先声明范围和不会修改的内容。
- 每个功能有 Red 到 Green 的测试结果。
- 至少记录一次 AI 首次方案的问题和修正。
- AI 负责解释、实现、测试和只读审查。
- 开发者负责数据库初始化、人工验收、commit、push、PR 和 merge。
- README 可以复现运行、迁移、测试和 Swagger 演示。
- 开发者能解释核心调用链和事务边界。

本次撤回三表模型不是失败，而是一次有效的 AI 协作决策：开发者审查了 AI 产出、发现范围超标，并要求系统回到可理解、可完成的目标。

## 16. 完成标准

满足以下条件才算完成：

- 一张 issues 业务表由 Alembic 创建。
- 五个业务接口可在 Swagger 完成 CRUD。
- 非法输入、404 和 204 行为符合设计。
- 所有默认测试通过。
- 专用 MySQL 测试库完成迁移和真实 CRUD 验收。
- main 保持可运行，功能通过 Pull Request 合并。
- AI 开发日志记录需求、生成、审查、纠错和证据。
- 开发者能够独立解释：

~~~text
请求
  -> Router
  -> Schema
  -> Service
  -> AsyncSession
  -> Issue Model
  -> MySQL
  -> Response
~~~

## 17. 未来扩展

以下内容只有在单表 MVP 完整收尾后才能重新评估：

- 项目分组。
- 多个候选方案历史。
- 搜索、筛选、分页和统计。
- 用户系统或前端。
- 大模型 API。

未来扩展不属于当前实现范围。
