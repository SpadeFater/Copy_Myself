# Copy_Myself

Copy_Myself is a LangGraph-based personal butler agent project. The current stage focuses on a standard development foundation plus a PyQt desktop workbench: graph orchestration, state, tools, memory, configuration, CLI, API, GUI, tests, and documentation.

## Current Status

- Goal confirmed: build a personal butler agent based on LangGraph.
- Framework status: standard foundation scaffold.
- Feature status: concrete butler abilities are intentionally left behind interfaces.

## Install

```powershell
python -m pip install -e .[dev]
```

For Office/WPS support:

```powershell
python -m pip install -e .[dev,office]
```

## Run

```powershell
copy-myself "what time is it in Asia/Shanghai?"
```

Or:

```powershell
python -m cli "帮我整理任务"
```

If Chinese text appears garbled in Windows PowerShell, switch the current
terminal session to UTF-8 before reading files or running commands that print
Chinese:

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

## Run API

```powershell
copy-myself-api
```

The API listens on `http://127.0.0.1:8000` and exposes:

- `GET /api/status`
- `POST /api/chat`
- `POST /api/approvals/{approval_id}`

Tool calls requiring confirmation return HTTP 202 with a `pending_approval`
object. Submit the decision to the approval endpoint with `session_id` and
`approved`; the same LangGraph execution then resumes.

## Run PyQt Workbench

```powershell
copy-myself-gui
```

The PyQt workbench uses `agent.service.ChatService` and does not require the
FastAPI server to be running.

### Workbench Interface

The desktop workbench uses a dark Fluent visual system with:

- role-aware, selectable chat bubbles with bounded scrolling for long replies;
- compact navigation for the workbench, persistent memory, and settings;
- a scan-friendly execution timeline plus a read-only expanded graph;
- model-provider and MCP import dialogs using the same visual tokens.

`PyQt6-Fluent-Widgets` supplies the Fluent theme integration. Its free edition
uses GPLv3; choose GPL-compatible distribution or obtain the appropriate
commercial licenses before distributing a closed-source build. The execution
graph uses a native PyQt6 renderer because NodeGraphQt 0.6.44 is not compatible
with the Qt 6.11 enum API used by the current environment.

## MCP Gateway

All tools run through the official Python MCP SDK. The agent opens one stdio
connection to `copy-myself-mcp-gateway`; the gateway maintains asynchronous
connections to the builtin stdio server and configured third-party stdio or
Streamable HTTP servers. Model-visible names use `service_id__tool`, while the
gateway audit/catalog identity uses `service_id/tool`.

Third-party calls always require confirmation. Builtin filesystem
`list/stat/read/search` calls run automatically; `write/mkdir/patch/copy/move/delete`
require a one-time approval bound to the session, canonical tool, argument
SHA-256, and TTL. CLI uses `y/N`, API uses HTTP 202 and the approval endpoint,
and the Qt GUI uses a non-blocking confirmation dialog.

## Built-In Tools

- `getTime`: returns the current time for an IANA timezone or supported location.
- `filesystem`: lists, reads, searches, writes, patches, copies, moves, and safely deletes files inside the configured workspace root.

The `filesystem` tool resolves every path before use, rejects paths outside allowed roots, blocks sensitive files such as `.git`, `.env`, and `keys`, extracts readable text from `.docx` files, requires hash checks before overwriting existing files, and moves confirmed deletes into `.trash/filesystem-tool/` by default. By default it allows the project directory plus the user's `Desktop`, `Documents`, and `Downloads`; add more roots with `COPY_MYSELF_FILESYSTEM_ROOTS` separated by the OS path separator.

## Test

```powershell
python -m pytest -v
python -m compileall -q .
```

## Structure

```text
agent/        LangGraph runtime, Gateway MCP client, coordinator, and ChatService
api/          FastAPI integration routes
builtin_mcp/  FastMCP server and builtin tool implementations
domain/       Pure business objects
gui/          PyQt desktop workbench
llm/          Model protocols and providers
memory/       Memory code package
mcp_gateway/  MCP proxy, connections, catalog, policy, approvals, and audit
memoryGraphData/ Runtime SQLite data
cli.py        Local command-line entry point
config.py     Environment-driven settings
app_logging.py Logging setup
docs/
  architecture.md
  superpowers/specs/
  superpowers/plans/
tests/
```

## Configure External MCP

Each service has a stable unique `service_id`, `stdio` or `streamable_http`
transport, a command plus argument array or endpoint, optional headers/env,
and a finite timeout. The reserved `builtin` ID cannot be configured by users.
The gateway isolates an offline external service so other tools and plain chat
remain available.

## Generated MCP Tools

When the model cannot satisfy a request with the current catalog, it may create
one generated MCP tool after approval. Generated tools are stored under
`builtin_mcp/tools/generated/<tool_id>/<version>/` with a manifest, source,
tests, and dependency lock data. Enabled versions are discovered by the
gateway refresh path and run as independent Docker-backed stdio services.

Generated tools must declare capabilities (`network`, filesystem access,
processes, or secrets). Docker runs use a read-only root filesystem, no Linux
capabilities, a non-root user, process/memory/CPU limits, and no network unless
the manifest explicitly requests it. PyPI and npm dependencies are installed
inside the image; npm install scripts remain disabled unless explicitly
approved. Failed validation or image builds leave the version disabled and do
not replace an existing active version.
