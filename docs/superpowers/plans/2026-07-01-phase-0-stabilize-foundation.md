# Phase 0 Stabilize Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the Copy_Myself foundation so the LangGraph, CLI, API, and PyQt workbench baseline is documented, tested, and ready for feature work.

**Architecture:** Keep the existing LangGraph, FastAPI, and PyQt boundaries unchanged. This milestone verifies the current baseline, removes stale browser-interface language, keeps IDE/cache artifacts out of version control, and records the result in project documentation.

**Tech Stack:** Python 3.11+, pytest, compileall, PyQt6, setuptools editable installs.

---

## File Structure

- `CONTRIBUTING.md`: contributor setup, verification commands, branch/commit rules, and PyQt GUI verification note.
- `.gitignore`: ignore Python caches, virtual environments, build outputs, local env files, IDE state, and generated dependency leftovers such as `node_modules`.
- `README.md`: keep user-facing commands aligned with the PyQt desktop workbench direction.
- `docs/architecture.md`: clarify that FastAPI is an integration layer and PyQt is the primary visual runtime.
- `docs/development-roadmap.md`: mark Phase 0 documentation hygiene items as complete after verification.
- `src/copy_myself/api/__init__.py`: remove stale GUI-runtime wording.
- `项目复盘与踩坑日志.md`: append Phase 0 verification and hygiene result.

## Tasks

### Task 1: Baseline Verification

**Files:**
- Read: existing source, tests, and docs

- [x] Run `python -m pytest -v`.
- [x] Run `python -m compileall -q src tests`.
- [x] Run `python -m pip install -e .[dev]`.
- [x] Run `copy-myself-gui` if PyQt6 installs and GUI launch is permitted.
- [x] Record any blocker before editing behavior.

### Task 2: Repository Hygiene

**Files:**
- Modify: `.gitignore`
- Create: `CONTRIBUTING.md`
- Git index: untrack `.idea/` without deleting local files

- [x] Expand `.gitignore` to cover local IDE files, Python build artifacts, test/cache outputs, virtual environments, local env files, and generated dependency/build outputs.
- [x] Add `CONTRIBUTING.md` with setup, test, GUI verification, and commit hygiene.
- [x] Remove `.idea/` from git tracking with `git rm -r --cached .idea`.

### Task 3: Documentation Alignment

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/development-roadmap.md`
- Modify: `src/copy_myself/api/__init__.py`
- Modify: `项目复盘与踩坑日志.md`

- [x] Replace stale GUI-runtime wording with PyQt desktop workbench or FastAPI integration wording.
- [x] Mark Phase 0 documentation hygiene items complete in the roadmap.
- [x] Append the verification result to the project review log.

### Task 4: Final Verification

**Files:**
- All changed files

- [x] Run `python -m pytest -v`.
- [x] Run `python -m compileall -q src tests`.
- [x] Run `python -m pip install -e .[dev]` if dependency installation was not already verified.
- [x] Run `copy-myself-gui` only after PyQt6 is installed and GUI launch is available.
- [x] Report exact commands and outcomes.
