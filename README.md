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
copy-myself "health check"
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
  tools/      Tool protocol, registry, and sample health tool
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
5. Add richer PyQt execution traces to the desktop workbench.
