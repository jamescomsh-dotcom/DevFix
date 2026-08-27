# DevFix 项目设计基线

本文档根据《DevFix_项目设计说明书_v1.0.md》整理，作为仓库内的实施基线。它记录本次 MVP 的边界、核心规则、阶段划分和仍需决策的问题；原说明书中的 AI 提示词、GitHub 流程与人工检查清单属于过程建议，不自动授予任何 Git 或外部平台写入权限。

## 1. 产品目标

DevFix 是个人开发问题知识库。它保存问题、候选解决方案、实际验证结果和最终有效方案，使一次开发排错形成可搜索、可统计、可复用的闭环。

核心流程：

```text
创建开发项目
  -> 记录问题
  -> 添加 AI、自主分析或文档方案
  -> 实际验证
  -> 标记失败、部分有效或成功
  -> 接受一个成功方案
  -> 自动解决问题
  -> 搜索和统计历史经验
```

第一版只有开发者本人使用，不需要用户表、登录或权限。

## 2. MVP 与非目标

MVP 包括：

- 项目、问题和解决尝试管理。
- 方案来源及验证结果记录。
- 成功方案接受和问题自动关闭。
- 问题筛选、关键词搜索、分页和项目统计。
- SQLAlchemy 全异步数据库访问。
- Alembic 数据库迁移。
- 可追溯的 AI 开发和人工验证记录。

MVP 不包括：

- 鉴权、多用户和团队协作。
- HTML/JavaScript 前端。
- 自动调用大模型 API。
- 文件上传、Redis、消息队列、后台任务和 WebSocket。
- Docker、Nginx、云部署和复杂全文检索。

## 3. 业务对象

```text
projects 1 ----- N issues 1 ----- N solution_attempts
```

### Project

- 名称唯一且非空。
- 可选说明。
- 使用 UTC 创建时间和更新时间。
- 删除项目时级联删除所属问题与尝试。

### Issue

- 属于一个 Project。
- 保存标题、描述、可选原始报错、分类和优先级。
- 分类：`BUG`、`QUESTION`、`CONFIG`、`OPTIMIZATION`。
- 优先级：`LOW`、`MEDIUM`、`HIGH`。
- 状态：`OPEN`、`IN_PROGRESS`、`RESOLVED`。
- 删除问题时级联删除解决尝试。

### SolutionAttempt

- 属于一个 Issue。
- 来源：`AI`、`SELF`、`DOCS`。
- 保存可选来源名称、提示词、方案正文和验证说明。
- 结果：`UNTESTED`、`FAILED`、`PARTIAL`、`SUCCESS`。
- `is_accepted` 表示是否为最终方案。

## 4. 状态与事务规则

```text
OPEN --添加第一个尝试--> IN_PROGRESS --接受 SUCCESS 尝试--> RESOLVED
```

必须满足：

1. 新问题默认 `OPEN`。
2. 新尝试默认 `UNTESTED` 且未接受。
3. 首个尝试把 `OPEN` 问题改为 `IN_PROGRESS`。
4. 只有 `SUCCESS` 尝试能成为最终方案。
5. 一个问题最多有一个已接受方案。
6. 普通 Issue PATCH 不能直接设为 `RESOLVED`。
7. 接受方案时，取消其他接受状态、接受当前方案、更新问题状态和 `resolved_at` 必须在同一事务中完成；失败时整体回滚。
8. MVP 不提供删除单个尝试的接口。

## 5. API 范围

系统接口保留在根路径：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 应用进程健康检查 |

后续业务 API 使用 `/api/v1` 前缀：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST/GET | `/projects` | 创建项目、项目列表 |
| GET/PATCH/DELETE | `/projects/{project_id}` | 项目详情、修改、删除 |
| POST | `/projects/{project_id}/issues` | 在项目下创建问题 |
| GET | `/issues` | 筛选、搜索和分页 |
| GET/PATCH/DELETE | `/issues/{issue_id}` | 问题详情、修改、删除 |
| POST | `/issues/{issue_id}/attempts` | 添加解决尝试 |
| PATCH | `/attempts/{attempt_id}` | 更新验证结果 |
| POST | `/issues/{issue_id}/attempts/{attempt_id}/accept` | 接受成功方案 |
| GET | `/projects/{project_id}/stats` | 项目问题统计 |

问题列表支持 `project_id`、`status`、`category`、`priority`、`keyword`、`page` 和 `page_size`；默认按创建时间倒序，`page_size` 范围为 1 到 100。

## 6. 技术结构

- Python 3.14
- FastAPI
- MySQL
- SQLAlchemy 2.x AsyncSession
- `asyncmy` 异步 MySQL 驱动
- Alembic
- Pydantic 2
- pytest + HTTPX

采用 Router + Service + Model + Schema，不增加 Repository 层：

- Router：HTTP 参数、响应模型和状态码。
- Service：查询、保存、业务规则、事务和业务异常。
- Model：映射、键、索引和关系。
- Schema：请求验证和响应边界。

应用启动禁止调用 `Base.metadata.create_all()`。数据库结构只由 Alembic 迁移管理。异步请求链不得混用同步 SQLAlchemy Session；详情关联应显式加载，避免异步懒加载。

## 7. HTTP 错误基线

| 场景 | 状态码 |
|---|---|
| 创建成功 | 201 |
| 读取或修改成功 | 200 |
| 删除成功且无响应体 | 204 |
| 参数验证失败 | 422 |
| 资源不存在 | 404 |
| 项目名称冲突 | 409 |
| 接受非 SUCCESS 方案 | 409 |
| 直接设为 RESOLVED | 409 |

业务冲突响应统一使用 `detail.code` 和 `detail.message`。

## 8. 分阶段交付

| 阶段 | 交付物 | 核心验收 |
|---|---|---|
| 0 | 骨架、README、设计文档、health | 应用启动；`/docs` 和 `/health` 可用 |
| 1 | 异步 Engine、Session、依赖 | 可执行异步查询；请求结束关闭 Session；不自动建表 |
| 2 | 三模型、关系、初始迁移 | 空库升级正确；Alembic current 与 heads 一致 |
| 3 | 项目 CRUD | 重名 409；缺失 404；级联删除正确 |
| 4 | 问题 CRUD | 默认 OPEN；不能直接改 RESOLVED |
| 5 | 尝试与接受事务 | 只有 SUCCESS 可接受；状态和唯一最终方案正确 |
| 6 | 搜索、分页、统计 | 组合筛选和统计准确 |
| 7 | README、示例、日志和展示 | 新环境可复现；完整闭环可演示 |

## 9. 后续阶段开始前需确认

设计说明书留下的以下问题不会在阶段 0 擅自固化：

1. Issue 状态是否完全由服务端事件管理，还是允许手工切换 `OPEN` 与 `IN_PROGRESS`。
2. 已解决问题能否重开、继续添加尝试或重新接受另一个成功方案。
3. 已接受方案能否被改成非 `SUCCESS`；建议禁止以保护不变量。
4. 尝试不属于路径中问题时统一返回 404 还是 409。
5. 并发接受方案时的锁策略；建议锁定 Issue 行后再更新全部尝试。
6. `resolution_rate` 在零问题时的值和小数精度。
7. 时间响应是否明确携带 UTC 标记，以及 `updated_at` 的更新责任。
8. 搜索的大小写、通配符转义和稳定二级排序规则。

这些决策应在影响相应阶段时写入测试和文档，而不是隐含在实现中。

