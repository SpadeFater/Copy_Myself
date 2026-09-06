<p align="center">
  <strong>Copy_Myself</strong>
</p>

<p align="center">
  <strong>一个将记忆、工具和确认流程接入桌面工作台的个人助理。</strong>
  <a href="https://github.com/SpadeFater/Copy_Myself">GitHub</a>
</p>

基于 LangGraph 的个人助理基础实现。它把对话、长期记忆、MCP 工具和人工确认放进同一条执行链，并提供 CLI、HTTP API 和 PyQt 桌面工作台三种入口。

**LangGraph** · **MCP** · **FastAPI** · **PyQt6** · **SQLite memory**

> [!NOTE]
> 项目当前处于基础能力建设阶段：核心运行链路、工具网关、记忆与桌面工作台已具备，复杂的个人助理工作流仍会继续完善。

## Install

需要 Python 3.11 或更高版本。

```powershell
python -m pip install -e .[dev]
```

需要控制 Microsoft Office 或 WPS 时，额外安装 Office 依赖：

```powershell
python -m pip install -e .[dev,office]
```

Windows PowerShell 中若中文输出乱码，可在当前会话启用 UTF-8：

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

## One agent, three surfaces.

所有入口都经由 `agent.service.ChatService`，所以 CLI、API 与桌面工作台共享同一条 LangGraph 执行链、记忆上下文与工具确认策略。

### CLI

适合一次性请求或终端交互：

```powershell
copy-myself "what time is it in Asia/Shanghai?"
```

也可以直接运行模块：

```powershell
python -m cli "帮我整理任务"
```

工具调用需要确认时，CLI 会提示 `Approve? [y/N]`；在非交互环境中会自动拒绝。

### API

```powershell
copy-myself-api
```

服务监听 `http://127.0.0.1:8000`，提供：

- `GET /api/status`
- `POST /api/chat`
- `POST /api/approvals/{approval_id}`

需要确认的工具调用会返回 HTTP `202` 和 `pending_approval`。提交带有 `session_id` 与 `approved` 的决定后，同一次 LangGraph 执行会恢复。

### Desktop workbench

```powershell
copy-myself-gui
```

PyQt 工作台直接使用 `ChatService`，不需要先启动 FastAPI。它提供会话视图、持久记忆浏览、执行时间线、只读执行图，以及模型和 MCP 服务配置入口。

> [!WARNING]
> `PyQt6-Fluent-Widgets` 的免费版本采用 GPLv3。发布闭源构建前，请确认分发方式符合 GPL，或取得相应的商业许可。

## Tools that ask before they act.

所有工具通过官方 Python MCP SDK 接入。Agent 与 `copy-myself-mcp-gateway` 建立一个 stdio 连接；网关负责连接内置工具和第三方 stdio 或 Streamable HTTP MCP 服务。

### Built-in tools

- `getTime`：返回 IANA 时区或已支持地点的当前时间。
- `filesystem`：在允许的根目录内列出、读取、搜索、写入、打补丁、复制、移动和安全删除文件。
- `office`：读取或操作 Word、Excel 和 PowerPoint；需要安装可选 Office 依赖。
- `create_tool`：在确认后创建、校验并安装一个生成式 MCP 工具。

模型可见的工具名使用 `service_id__tool`，网关的目录和审计身份使用 `service_id/tool`。

### Approval model

第三方工具调用始终需要确认。内置工具中，读取文件、查看属性、搜索和获取时间可自动执行；写入、建目录、补丁、复制、移动、删除、Office 修改与生成工具均需确认。

确认记录绑定会话、规范化工具名、参数 SHA-256 与有效期。CLI 以 `y/N` 处理，API 返回 HTTP `202`，GUI 使用非阻塞确认对话框。

### Filesystem guardrails

`filesystem` 会在执行前解析路径并拒绝允许根目录外的访问；`.git`、`.env`、密钥文件等敏感路径不可操作。覆盖已有文件或应用补丁需要匹配 SHA-256，删除默认仅演练，确认后会移入 `.trash/filesystem-tool/`。

默认允许当前项目目录。通过 `COPY_MYSELF_FILESYSTEM_ROOTS` 配置额外根目录，多个路径使用操作系统路径分隔符。

## Memory that stays with the work.

每次请求都会经过一条明确的 LangGraph 流程：

```text
load_memory -> classify_intent -> select_tool -> run_tool -> create_response -> save_memory
```

记忆实现位于 `memory/`，运行时 SQLite 数据默认写入 `memoryGraphData/memory_graph.sqlite3`。运行数据与 Python 包分离，便于替换记忆存储而不影响 Agent 编排。

## Configure models and MCP.

模型供应商配置默认存放在 `~/.copy_myself/models.json`，外部 MCP 服务配置默认存放在 `~/.copy_myself/mcp_services.json`。可通过环境变量改用其他目录或文件：

```powershell
$env:COPY_MYSELF_CONFIG_DIR = "C:\path\to\config"
$env:COPY_MYSELF_MODEL_SETTINGS_PATH = "C:\path\to\models.json"
$env:COPY_MYSELF_MCP_SERVICES_PATH = "C:\path\to\mcp_services.json"
```

外部 MCP 服务需要稳定且唯一的 `service_id`，可使用 `stdio` 或 `streamable_http` 传输方式，并配置命令与参数或服务端点、可选请求头/环境变量及超时。`builtin` 为保留 ID，不能由用户配置。

已保存的模型配置可以重新探测上游模型目录。GUI 的“设置 -> 模型”中选中配置后点击“更新上游模型”；命令行可使用：

```powershell
copy-myself models refresh "provider name" --json
copy-myself models rollback --json
```

本地 API 提供 `POST /api/models/{provider_name}/refresh` 和 `POST /api/models/rollback`。刷新会更新 `available_models`，保留当前模型；如果当前模型下线或验证失败，会在结果中标记不可用而不会自动切换。刷新前的完整配置保存在 `models.json.bak`，可通过 GUI、API 或 CLI 回滚。

当某个外部服务离线时，网关会将其隔离，其余工具与普通对话仍可使用。

## Generated MCP tools.

当现有工具目录无法满足请求时，模型可在获得确认后生成一个 MCP 工具。每个版本保存在：

```text
builtin_mcp/tools/generated/<tool_id>/<version>/
```

目录包含清单、源码、测试和依赖锁定数据。工具版本在网关刷新时被发现，并作为独立的 Docker stdio 服务运行。

生成工具必须声明能力，例如网络、文件系统、进程或密钥访问。Docker 运行时采用只读根文件系统、非 root 用户、资源限制且默认无网络；校验或镜像构建失败不会替换现有启用版本。

## Project layout

```text
agent/        LangGraph runtime、工具选择与 ChatService
api/          FastAPI 应用、路由与会话存储
builtin_mcp/  内置 FastMCP 服务及工具实现
domain/       纯业务对象
gui/          PyQt 桌面工作台与视图模型
llm/          模型协议与 OpenAI-compatible provider
memory/       记忆存储、抽取与图结构实现
mcp_gateway/  MCP 连接、目录、策略、确认与审计
cli.py        本地命令行入口
config.py     环境变量和本地配置读写
```

## Development

完成后端或 GUI 逻辑变更前，运行：

```powershell
python -m pytest -v
python -m compileall -q .
```

修改 PyQt 界面后，还应实际启动工作台：

```powershell
copy-myself-gui
```

详细约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## Philosophy

Copy_Myself 的方向很直接：让个人助理能记住上下文、调用真实工具，并在影响外部状态前把决定交回给人。

- LangGraph 负责可观察、可恢复的编排边界。
- MCP 统一内置能力与外部服务的接入方式。
- 确认机制绑定具体会话与具体参数，而不是给工具一张永久通行证。
- GUI、API 与 CLI 是同一个 Agent 的不同入口，不是三套独立逻辑。

_为需要持续对话，也需要清醒确认的个人工作流而做。_
