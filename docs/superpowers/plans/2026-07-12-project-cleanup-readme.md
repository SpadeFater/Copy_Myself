# Project Cleanup And README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean invalid project artifacts, fix repository hygiene, and rewrite `README.md` around the current Copy_Myself runtime.

**Architecture:** This is a repository hygiene and documentation slice. It does not remove working agent, GUI, memory, API, or tool modules because the current test suite verifies those paths. Runtime data and local-only files stay ignored, while user-facing setup docs describe the current PyQt-first product direction.

**Tech Stack:** Python 3.11+, LangGraph, PyQt6, FastAPI, pytest, SQLite.

---

### Task 1: Repository Hygiene

**Files:**
- Modify: `.gitignore`
- Modify: `.env.example`
- Remove locally generated artifacts only: `.pytest_cache/`, `__pycache__/`, `src/copy_myself.egg-info/`, `memory/`, `.idea/`

- [ ] **Step 1: tighten ignore rules**

Keep Python caches, build outputs, local environments, runtime memory, IDE state, and local key files ignored. Do not ignore all root Markdown files, because project docs and logs should be explicit.

- [ ] **Step 2: refresh environment example**

Keep only current Copy_Myself variables: app name, log level, active model, model name, API key, base URL, model profiles, and MCP services. Remove retired frontend variables.

- [ ] **Step 3: remove generated local artifacts**

Delete ignored caches and runtime outputs from the working tree. Do not read or delete the untracked `keys` file; keep it ignored as a local secret.

### Task 2: README Rewrite

**Files:**
- Modify: `README.md`

- [ ] **Step 1: rewrite README in Chinese**

Cover project purpose, current status, install, CLI/API/PyQt run commands, model settings, MCP import, memory files, structure, cleanup notes, verification, and next milestones.

- [ ] **Step 2: remove stale wording**

Avoid frontend/Vite/browser-interface references. Make PyQt the primary GUI surface and FastAPI an integration surface.

### Task 3: Verification And Review Log

**Files:**
- Modify: `docs/project-review-log.md`
- Modify: `项目复盘与踩坑日志.md`

- [ ] **Step 1: run verification**

Run:

```powershell
python -m pytest -v
python -m compileall -q src tests
```

- [ ] **Step 2: record results**

Append a short cleanup entry to the project review log and project retrospective log, including verification commands and remaining warning if present.
