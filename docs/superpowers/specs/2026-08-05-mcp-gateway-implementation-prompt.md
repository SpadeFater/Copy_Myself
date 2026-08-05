# Copy_Myself MCP Gateway 重构实施提示词

你正在 `D:\Pycharm\Copy_Myself` 项目中工作。请完整实施 MCP Gateway 工具运行时重构。

开始前必须完整阅读并遵循：

1. `D:\codexplace\AGENTS.md`
2. `D:\Pycharm\Copy_Myself\AGENTS.md`
3. `D:\Pycharm\Copy_Myself\docs\superpowers\specs\2026-08-05-mcp-gateway-tool-runtime-design.md`

设计文档是本任务的权威需求。不要只做脚手架、局部演示或保留双轨运行；最终必须删除 Agent 直接调用本地工具的旁路。

## 核心目标

- Agent 只能连接 CopyMyself MCP Gateway；
- Gateway 连接 builtin MCP Server 和第三方 MCP Server；
- 内置 `getTime`、filesystem 以及未来内置工具全部通过 MCP；
- 下游支持 `stdio` 与 Streamable HTTP；
- 第三方工具每次调用都要求用户确认；
- 内置只读操作自动执行，有副作用或未知风险操作要求确认；
- GUI、CLI、API 都能暂停、确认、拒绝并恢复同一次 LangGraph 执行；
- 使用服务命名空间解决工具重名；
- 每次实际调用都有脱敏审计记录。

## 强制架构

```text
GUI / CLI / API
  -> Agent + ToolExecutionCoordinator
  -> MCP over stdio
  -> CopyMyself MCP Gateway
       -> builtin MCP Server over stdio
       -> third-party MCP over stdio
       -> third-party MCP over Streamable HTTP
```

模块至少按职责拆分为：

```text
mcp_gateway/
  server.py
  connections.py
  catalog.py
  naming.py
  policy.py
  approvals.py
  audit.py
  errors.py

builtin_mcp/
  server.py
  tools/filesystem.py
  tools/time.py

agent/
  mcp_client.py
  tool_execution.py
```

遵循项目现有模块化规则。可以根据现有代码适度调整文件名，但不得合并成单个大型模块。

## 实施要求

1. 使用官方 Python MCP SDK；不要自研 JSON-RPC 或 transport。
2. builtin MCP 使用 FastMCP；动态 Gateway 使用适合代理 `tools/list` 和 `tools/call` 的低层 Server API。
3. Agent 到 Gateway 首期使用 stdio；Gateway 下游支持 stdio 和 Streamable HTTP。
4. 使用异步 MCP 生命周期，不得每次调用新建 event loop 或会话。
5. 模型工具名使用 `<service_id>__<tool>`；Gateway canonical name 使用 `<service_id>/<tool>`。
6. Gateway 内部审批控制工具不得传给模型。
7. 第三方工具 annotations 不可信，每次调用必须确认。
8. 内置工具缺少风险声明时默认确认。
9. filesystem 的 `list/stat/read/search` 自动执行；`write/mkdir/patch/copy/move/delete` 必须确认。
10. 保留 filesystem 的允许根、敏感路径、hash、dry-run、确认和回收站保护。
11. 批准必须绑定 session、服务、工具、参数 hash 和 TTL，只能消费一次。
12. 用户拒绝、批准过期或 session 不匹配时，不得调用下游。
13. 使用 LangGraph `interrupt` 和 checkpointer 实现暂停恢复。
14. API 待确认返回 HTTP 202，并新增 `POST /api/approvals/{approval_id}`。
15. CLI 使用默认拒绝的 `y/N`；非交互环境拒绝需确认调用。
16. GUI 使用非阻塞确认对话框，MCP 调用不得阻塞 Qt 主线程。
17. 单个第三方服务故障不得影响其他服务或纯聊天。
18. 有副作用调用结果未知时不得自动重试。
19. stdio 命令不得经过 shell 拼接；日志必须脱敏。
20. 迁移结束后删除 `ToolRegistry` 的运行职责和旧本地执行路径。

## 建议实施顺序

按设计文档的五个阶段执行：

1. MCP 基础设施与 `getTime` 端到端链路；
2. filesystem 迁移、风险策略和 Gateway 审批；
3. Agent MCP Client、LangGraph interrupt 与 resume；
4. API、CLI、GUI 接入；
5. 第三方 stdio/Streamable HTTP、清理、文档和审计。

每个阶段先写最小失败测试，再实现，再运行相关测试。不要在旧链路尚未被新链路覆盖时提前删除可运行代码；最终验收前必须删除旧旁路。

## 必测场景

- Gateway 通过 stdio 发现并调用 builtin `getTime`；
- filesystem 读取无需确认；
- filesystem 写入确认前下游调用数为零；
- 所有第三方工具每次调用都中断确认；
- 批准后只执行一次；
- 拒绝、过期、重复批准、跨 session 批准均不执行；
- 参数或参数 hash 改变后旧批准失效；
- stdio 与 Streamable HTTP 第三方服务均可发现和调用；
- 服务命名空间归一化后冲突可检测；
- 单服务离线不影响其他服务；
- Gateway 不可用时纯聊天仍可工作；
- API 的 200、202 和 approval endpoint；
- CLI 和 GUI 的批准、拒绝及恢复；
- Agent 代码不再导入或实例化具体内置工具；
- 所有实际执行都产生脱敏 Gateway 审计记录。

## 验证与交付

至少执行：

```powershell
python -m pytest -v
python -m compileall -q .
```

同时运行针对真实 stdio 子进程和 Streamable HTTP 测试服务的集成测试。所有子进程必须在测试结束后清理。

更新：

- `README.md`
- 相关架构文档
- `D:\Pycharm\Copy_Myself\复盘与踩坑日志.md`

最终交付时报告：

- 关键架构变化；
- 旧旁路删除情况；
- 权限和审批行为；
- 精确测试命令与结果；
- 尚存限制或风险。

不要声称完成，除非所有验收标准有新鲜验证证据。
