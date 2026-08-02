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

## Run

```powershell
copy-myself "what time is it in Asia/Shanghai?"
```

Or:

```powershell
python -m copy_myself.cli "帮我整理任务"
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

## Run PyQt Workbench

```powershell
copy-myself-gui
```

The PyQt workbench calls the LangGraph agent directly and does not require the
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

## Built-In Tools

- `getTime`: returns the current time for an IANA timezone or supported location.
- `filesystem`: lists, reads, searches, writes, patches, copies, moves, and safely deletes files inside the configured workspace root.

The `filesystem` tool resolves every path before use, rejects paths outside allowed roots, blocks sensitive files such as `.git`, `.env`, and `keys`, extracts readable text from `.docx` files, requires hash checks before overwriting existing files, and moves confirmed deletes into `.trash/filesystem-tool/` by default. By default it allows the project directory plus the user's `Desktop`, `Documents`, and `Downloads`; add more roots with `COPY_MYSELF_FILESYSTEM_ROOTS` separated by the OS path separator.

## Test

```powershell
python -m pytest -v
python -m compileall -q src tests
```

## Structure

```text
src/copy_myself/
  agent/      LangGraph state, nodes, and graph assembly
  api/        FastAPI integration routes
  gui/        PyQt desktop workbench
  memory/     Memory protocol and in-memory implementation
  tools/      Tool protocol, registry, time tool, and filesystem tool
  cli.py      Local command-line entry point
  config.py   Environment-driven settings
  logging.py  Logging setup
docs/
  architecture.md
  superpowers/specs/
  superpowers/plans/
tests/
```

## Next Milestones

1. Decide the first concrete personal-butler capability.
2. Add a real LLM adapter behind the existing node boundary.
3. Replace in-memory storage with persistent memory.
4. Add richer tool modules for tasks, reminders, notes, or schedules.
5. Feed real per-node timing and status events into the execution trace.
