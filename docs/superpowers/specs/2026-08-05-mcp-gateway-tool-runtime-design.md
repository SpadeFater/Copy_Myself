# MCP Gateway Tool Runtime Design

## 1. 目标

重构 Copy_Myself 的工具调用机制，使 Agent 不再直接执行任何内置工具。所有内置工具和第三方工具都必须通过 MCP 协议发现和调用，并由统一 MCP Gateway 完成聚合、命名、权限判断、审批、转发和审计。

本设计覆盖以下已确认需求：

- 内置工具运行在独立 MCP Server 中；
- Agent 只连接 CopyMyself MCP Gateway；
- Gateway 支持连接 `stdio` 和 Streamable HTTP 下游 MCP 服务；
- 第三方服务启用后自动发现全部工具；
- 每次第三方工具调用都必须由用户确认；
- 内置只读操作自动执行，内置有副作用操作必须确认；
- GUI、CLI、API 均支持暂停、确认、拒绝和恢复；
- 工具使用服务命名空间，避免跨服务重名；
- 后续新增内置工具只需进入对应内置工具模块并注册到内置 MCP Server，不修改 Agent。

## 2. 非目标

- 不改变现有记忆模型和 SQLite 数据结构；
- 不重写 LLM provider 协议；
- 不自研 MCP JSON-RPC、握手或传输实现；
- 首期不提供跨进程重启后的待审批恢复；
- 首期不建设多 Agent 共享、远程集中部署的 Gateway 集群；
- 不为每个小型内置工具单独启动 MCP Server；
- 不保留 Agent 直接调用 Python 工具类的兼容旁路。

## 3. 当前状态与问题

当前 `TimeTool` 和 `FileSystemTool` 被直接注册到 `ToolRegistry`。模型通过 OpenAI-compatible `tools/tool_calls` 选择工具后，Agent 在本进程内调用 `registry.run()`。这不是 MCP 调用。

项目已有 `McpServiceSettings`、配置文件读写和 GUI 导入界面，但尚无 MCP SDK、MCP Client、MCP Server、`tools/list`、`tools/call` 或真实 transport 生命周期。

主要问题：

- 内置工具与第三方 MCP 工具存在两套机制；
- Agent 依赖具体本地工具注册表；
- 第三方 MCP 配置不能实际连接或执行；
- 权限确认缺少跨 GUI、CLI、API 的统一状态模型；
- 新增内置工具需要修改 Agent 运行时依赖。

## 4. 方案选择

采用统一 MCP Gateway：Agent 只连接一个 Gateway；Gateway 连接一个内置 MCP Server 和任意数量第三方 MCP Server。

```text
GUI / CLI / API
       |
       v
Agent + ToolExecutionCoordinator
       |
       | MCP over stdio
       v
CopyMyself MCP Gateway
       |-- builtin MCP Server (stdio)
       |     |-- filesystem
       |     |-- getTime
       |     `-- future built-in tools
       |-- third-party local MCP servers (stdio)
       `-- third-party remote MCP servers (Streamable HTTP)
```

选择 Gateway 而不是 Agent 直连多个服务，原因是权限、命名、审计和连接状态需要集中治理。代价是增加一个本地进程和代理层，但 Agent 边界更稳定，也保留了未来多 Agent 共享 Gateway 的演进路径。

## 5. 核心约束

1. Agent 不得导入、实例化或直接运行任何内置工具。
2. 所有业务工具执行都必须产生 Gateway MCP 调用记录。
3. Gateway 不包含具体业务工具实现，只代理并治理工具。
4. 内置工具实现只存在于 `builtin_mcp` 模块。
5. Gateway 连接失败不能让纯聊天能力崩溃。
6. 未知风险默认按有副作用处理。
7. 用户批准只绑定一次调用的服务、工具和参数，不能复用。

## 6. 模块设计

```text
mcp_gateway/
  __init__.py
  server.py          # 面向 Agent 的动态 MCP Server
  connections.py     # 下游 stdio / Streamable HTTP 会话生命周期
  catalog.py         # tools/list 聚合、映射和刷新
  naming.py          # 服务 ID 与模型安全工具名转换
  policy.py          # 来源和风险判定
  approvals.py       # 待审批记录、过期、拒绝和一次性消费
  audit.py           # 结构化调用审计
  errors.py          # 稳定错误码和结果结构

builtin_mcp/
  __init__.py
  server.py          # FastMCP 服务入口和显式工具注册
  tools/
    __init__.py
    filesystem.py
    time.py

agent/
  mcp_client.py      # 只连接 Gateway
  tool_execution.py  # 模型调用、MCP 调用、interrupt 和 resume
```

项目使用官方 Python MCP SDK：

- `builtin_mcp` 使用 `FastMCP` 暴露固定工具；
- `mcp_gateway` 使用低层 Server API 动态返回下游工具目录并代理调用；
- Agent 和 Gateway 下游连接使用 SDK 的 `ClientSession`；
- 本地连接使用 `stdio_client`；
- 远程连接使用 `streamable_http_client`。

不手写 MCP transport 或 JSON-RPC。实现时选择与 Python 3.11 兼容、经过测试的 SDK 版本，并在 `pyproject.toml` 记录明确下限。

## 7. 进程与生命周期

首期采用每个应用实例一个 Gateway 子进程：

```text
copy-myself / copy-myself-api / copy-myself-gui
  `-- starts copy-myself-mcp-gateway over stdio
        `-- starts copy-myself-builtin-mcp over stdio
```

Gateway 再根据配置启动第三方 stdio 服务或连接远程 Streamable HTTP 服务。应用退出时按相反顺序关闭会话和子进程。

这样无需占用固定端口，也避免 GUI、CLI、API 同时运行时发生端口冲突。未来共享 Gateway 时，可为 Gateway 增加 Streamable HTTP 上游 transport，Agent 接口保持 MCP Client 不变。

MCP SDK 以异步 API 为核心：

- Agent MCP Client 和 Gateway connection manager 使用异步实现；
- API 路由使用异步 ChatService 接口；
- CLI 由单一 `asyncio.run()` 入口驱动；
- GUI 在后台 worker 中运行异步调用，禁止阻塞 Qt 主线程；
- 不在每次工具调用时新建 event loop 或 MCP 会话。

## 8. 服务配置

扩展 `McpServiceSettings`：

```text
service_id       稳定且唯一的机器标识
name             用户可见名称
transport        stdio | streamable_http
command          stdio 启动命令
args             stdio 参数数组
endpoint         Streamable HTTP URL
headers          HTTP headers 或环境变量引用
enabled          是否启用
timeout_seconds  调用超时
```

规则：

- `builtin` 是保留 `service_id`，由运行时注入，不能通过 GUI 覆盖；
- `service_id` 只允许小写字母、数字、`-` 和 `_`；
- 多个服务不能使用相同 `service_id`；
- `stdio` 命令和参数以数组传递，禁止 shell 字符串拼接；
- HTTP 密钥优先使用环境变量引用，日志中必须脱敏；
- `sse` 不在首期支持范围。

现有 MCP 配置需要兼容迁移：缺少 `service_id` 时，根据名称生成并持久化稳定 slug；原 `http` transport 规范化为 `streamable_http`。

## 9. 工具发现与命名

Gateway 启动时连接所有启用服务并调用 `tools/list`。目录项至少保存：

```text
service_id
downstream_name
canonical_name
model_name
description
input_schema
annotations
origin
connection_status
```

命名分三层：

- 下游原名：例如 `search`；
- Gateway canonical name：例如 `github/search`；
- 模型安全名：例如 `github__search`。

模型侧不使用点号，因为部分 OpenAI-compatible API 对 function name 只接受字母、数字、下划线和连字符。`naming.py` 必须提供可逆映射，并在归一化后检测冲突。

Gateway 接收下游 `notifications/tools/list_changed` 后刷新对应服务目录，再向 Agent 发出工具目录变化通知。离线服务的工具不继续暴露为可调用状态。

Gateway 自身的审批控制工具属于内部工具，只允许 `ToolExecutionCoordinator` 调用，不进入传给模型的工具定义列表。

## 10. 权限策略

策略按以下优先级判断：

1. 第三方来源：每次调用必须确认，不信任其 read-only annotations；
2. 内置工具显式声明只读：自动执行；
3. 内置工具显式声明有副作用：必须确认；
4. 内置工具缺少或无法解析风险声明：必须确认。

`filesystem` 保留单工具多 action 契约时，内置 MCP Server 在受信任 `_meta` 中声明参数级策略：

- `list`、`stat`、`read`、`search`：只读；
- `write`、`mkdir`、`patch`、`copy`、`move`、`delete`：有副作用。

后续内置工具优先使用标准 MCP annotations。只有风险随参数变化时才使用项目自定义 `_meta.copy_myself` 策略。Gateway 只信任 `builtin` 服务提供的自定义策略。

原有 filesystem 防护继续生效：允许根目录、路径解析、敏感文件拦截、覆盖前哈希校验、删除 dry-run、明确确认和回收站移动均不能因 Gateway 审批而移除。Gateway 审批与工具自身校验是两层防护。

## 11. 审批协议

### 11.1 创建待审批调用

Agent 正常调用 Gateway 的代理工具。Gateway 在策略判定需要确认时不调用下游，而是创建待审批记录并返回结构化结果：

```json
{
  "code": "approval_required",
  "approval_id": "opaque-one-time-id",
  "service_id": "github",
  "tool": "github/search",
  "arguments": {},
  "summary": "准备调用第三方工具 github/search",
  "expires_at": "2026-08-05T12:00:00+08:00"
}
```

待审批记录保存在 Gateway 内存中，包含所属 MCP session、canonical tool name、规范化参数、参数 SHA-256、创建时间、过期时间和状态。

### 11.2 用户决策

Gateway 暴露一个内部 MCP 控制工具，用于提交 `approval_id` 和 `approved`。Agent 的 MCP Client 可以调用它，但该工具不会传给模型。

- 批准：Gateway 原子地将记录从 pending 改为 executing，执行原始下游调用并返回结果；
- 拒绝：Gateway 标记 rejected，返回 `user_rejected`，不调用下游；
- 过期：返回 `approval_expired`；
- 重复提交：返回 `approval_already_resolved`；
- session 不匹配：返回 `approval_session_mismatch`。

模型无法构造批准，因为模型看不到内部控制工具，且业务工具参数中不存在 `approved` 或 `approval_id` 字段。

### 11.3 Agent 暂停与恢复

使用 LangGraph `interrupt` 和 checkpointer：

```text
Gateway returns approval_required
  -> ToolExecutionCoordinator records pending approval
  -> LangGraph interrupt
  -> interface asks user
  -> ChatService.resume(approval_id, approved)
  -> internal Gateway approval tool resolves and executes/rejects
  -> LangGraph Command(resume=...)
  -> model receives tool result and continues
```

首期使用进程内 checkpointer。应用或 Gateway 重启时待审批记录失效，绝不自动执行或重放。

## 12. Agent 数据流

正常只读调用：

```text
LLM selects builtin__getTime
  -> ToolExecutionCoordinator maps model name to Gateway name
  -> MCP tools/call to Gateway
  -> Gateway policy allows
  -> Gateway tools/call to builtin MCP
  -> result returns through Gateway
  -> LLM receives tool result
  -> final response
```

需确认调用：

```text
LLM selects thirdparty__tool
  -> MCP tools/call to Gateway
  -> Gateway returns approval_required without downstream call
  -> LangGraph interrupts
  -> user approves
  -> Agent calls hidden Gateway approval control tool
  -> Gateway executes stored downstream call once
  -> LangGraph resumes with result
  -> final response
```

迁移后删除确定性意图节点对 `getTime` 和 `filesystem` 的本地执行分支。允许意图分类继续辅助提示，但不得绕过模型工具选择或 MCP Gateway。

首期保持一次模型响应处理一个工具调用的现有行为。多工具循环属于后续独立增强，不应混入本次协议迁移。

## 13. 应用接口

`ChatService` 提供统一能力：

```text
achat(message, session_id) -> ChatRunResult
resume(approval_id, approved, session_id) -> ChatRunResult
```

`ChatRunResult.status`：

```text
completed | pending_approval | failed
```

待确认结果包含稳定的 `PendingApproval` DTO。GUI、CLI、API 不读取 LangGraph 内部状态字段。

### API

`POST /api/chat`：

- 完成时返回 HTTP 200；
- 待确认时返回 HTTP 202 和 approval DTO；
- `session_id` 同时作为 LangGraph `thread_id`。

新增：

```http
POST /api/approvals/{approval_id}
Content-Type: application/json

{
  "session_id": "...",
  "approved": true
}
```

批准或拒绝后返回恢复执行的 `ChatResponse`。若恢复过程中产生新的待审批调用，仍返回 202。

### CLI

CLI 收到 pending approval 后输出服务、工具、参数摘要，并使用默认拒绝的 `y/N` 提示。非交互环境无法确认时拒绝调用并返回明确错误。

### GUI

GUI 使用非阻塞确认对话框显示服务、工具、参数和风险来源。用户决策通过后台 worker 调用 `ChatService.resume()`；等待期间禁用重复提交，但聊天界面保持响应。

## 14. 错误处理

稳定错误码包括：

```text
gateway_unavailable
service_start_failed
service_offline
tool_not_found
tool_schema_invalid
tool_timeout
tool_call_failed
approval_required
approval_expired
approval_already_resolved
approval_session_mismatch
user_rejected
```

行为要求：

- 单个第三方服务失败时隔离该服务，其他服务继续工作；
- builtin 启动失败时纯聊天继续可用，并明确显示内置工具不可用；
- 下游调用设置有限超时；超时后不盲目自动重试有副作用调用；
- 连接建立失败允许有限重连，不能无限阻塞启动；
- 已开始但结果未知的有副作用调用返回明确“不确定状态”，禁止自动重放；
- MCP 原始异常在边界处转换为稳定错误码，同时保留脱敏诊断日志。

## 15. 安全与审计

每次代理调用记录：

```text
request_id
session_id
service_id
canonical_tool
argument_hash
approval_required
approval_id（如有）
decision
started_at
duration_ms
outcome
error_code
```

日志不得记录 API key、Authorization header、完整敏感参数或完整工具结果。参数默认只记录 hash 和经过工具定义声明的安全摘要。

其他安全要求：

- 第三方 stdio 程序继承最小必要环境变量；
- 禁止通过 shell 执行拼接命令；
- HTTP 仅允许配置明确 endpoint；
- Gateway 不把内部审批工具暴露给模型；
- approval ID 使用不可预测随机值，并绑定 session；
- 所有批准一次性消费且有短 TTL；
- 用户批准不能替代下游工具自身输入校验。

## 16. 新增内置工具流程

贡献者新增内置工具时：

1. 在 `builtin_mcp/tools/` 创建单一职责模块；
2. 使用 FastMCP 注册工具和 JSON Schema；
3. 声明标准 MCP annotations；
4. 若风险依赖参数，声明受信任的项目策略元数据；
5. 在 `builtin_mcp/server.py` 的显式注册列表加入模块；
6. 添加通过 MCP Client 调用的测试；
7. 不修改 Agent、Gateway 代理逻辑或模型 provider。

显式注册优于自动扫描导入：启动行为可审查、错误更清楚，也避免导入任意文件产生副作用。未来需要独立安装的内置扩展时，再引入 Python entry points，不在首期实现。

## 17. 迁移阶段

### 阶段一：建立 MCP 基础设施

- 添加官方 MCP SDK 依赖；
- 建立 builtin MCP Server 和 Gateway 最小服务；
- 实现 stdio 上下游连接、目录聚合和命名映射；
- 将 `getTime` 迁移并通过 Gateway 端到端验证。

### 阶段二：迁移 filesystem 与权限策略

- 将 filesystem 实现移入 `builtin_mcp/tools`；
- 保留全部安全行为；
- 添加参数级读写风险元数据；
- 实现 Gateway policy、approval store 和内部审批工具。

### 阶段三：接入 Agent 暂停恢复

- 添加 Agent MCP Client 和 ToolExecutionCoordinator；
- 用 MCP 工具目录替换 `ToolRegistry.definitions()`；
- 用 LangGraph interrupt/checkpointer 实现确认；
- 删除 Agent 本地工具执行分支。

### 阶段四：接入三个应用入口

- API 改为 async chat，增加 approval endpoint 和 202 响应；
- CLI 增加交互确认；
- GUI 增加非阻塞确认对话框；
- 统一使用 `ChatService.resume()`。

### 阶段五：第三方服务与清理

- 实现第三方 stdio 和 Streamable HTTP 连接；
- 将现有 MCP 配置真正接入 Gateway；
- 增加服务状态展示和脱敏审计；
- 删除 `ToolRegistry`、旧工具注册和无用兼容代码；
- 更新 README、架构文档和项目复盘日志。

每个阶段必须保持测试可运行，不允许先删除旧路径再留下不可执行的中间状态。最终阶段必须彻底移除本地旁路。

## 18. 测试策略

### 单元测试

- 服务 ID 和工具名规范化、可逆映射、冲突检测；
- 第三方始终确认；
- 内置只读自动执行；
- 内置有副作用和未知风险要求确认；
- approval TTL、session 绑定、一次性消费、拒绝和参数 hash；
- 配置迁移与 transport 规范化；
- 稳定错误映射和日志脱敏。

### MCP 集成测试

- 真实启动 builtin stdio MCP Server；
- Gateway 发现并代理 `getTime`；
- Gateway 代理 filesystem 读取；
- filesystem 写入在确认前零下游调用；
- 模拟第三方 stdio MCP；
- 模拟第三方 Streamable HTTP MCP；
- 单服务离线不影响其他服务；
- `tools/list_changed` 触发目录刷新。

### Agent 集成测试

- 模型收到的只有 Gateway 聚合工具；
- Agent 不实例化本地工具；
- 只读调用完成一次 MCP 往返；
- 第三方调用每次中断确认；
- 用户拒绝后下游调用计数为零；
- 用户批准后只执行一次；
- 重复、过期或跨 session 批准被拒绝；
- Gateway 失败时纯聊天仍可完成。

### 接口测试

- API 200 正常完成；
- API 202 返回待审批 DTO；
- approval endpoint 批准、拒绝、过期和 session 不匹配；
- CLI 默认拒绝和批准恢复；
- GUI 对话框展示、重复提交保护和后台恢复。

### 回归验证

```powershell
python -m pytest -v
python -m compileall -q .
```

涉及真实子进程和网络 transport 的测试必须有明确超时和清理，不能留下 MCP 子进程。

## 19. 验收标准

- Agent、API、GUI、CLI 不导入或实例化任何具体内置工具；
- `ToolRegistry` 不再承担运行时工具发现或执行职责；
- `getTime` 和 filesystem 均通过 builtin MCP Server 与 Gateway 调用；
- Gateway 支持下游 stdio 和 Streamable HTTP；
- 启用的第三方服务工具自动出现在统一目录；
- 工具名带稳定服务命名空间，冲突可检测；
- 每次第三方调用必须确认；
- 内置只读自动执行，有副作用调用必须确认；
- GUI、CLI、API 都能确认、拒绝和恢复；
- 未批准、拒绝、过期或参数不匹配时下游零执行；
- 每次实际工具执行都有脱敏 Gateway 审计记录；
- 无本地执行旁路；
- 全量测试和 compileall 通过；
- README、架构说明和项目复盘日志与新机制一致。

## 20. 后续演进

本次不实现，但当前边界允许后续增加：

- Agent 通过 Streamable HTTP 连接共享 Gateway；
- 多 Agent 共用集中策略和审计；
- 持久化 checkpointer 与跨重启审批恢复；
- Python entry points 安装独立内置扩展；
- 每服务 allowlist、速率限制和资源配额；
- 多工具循环和并行只读调用；
- 旧 SSE transport 兼容层。
