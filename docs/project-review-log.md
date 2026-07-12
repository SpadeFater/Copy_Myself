# Project Review Log

## 2026-07-10 Memory Graph

- Added a local-first graph memory design where completed user-assistant turns become durable SQLite memory nodes.
- Kept the older JSONL `PersistentMemoryStore` available while making `GraphMemoryStore` the PyQt workbench default.
- Verified the first implementation with focused memory, agent, and GUI tests before running full project verification.
- Retired the old brief-memory mechanism: JSONL memory now exists only for complete-memory display/archive and no longer feeds model context.

## 2026-07-11 Memory Graph Verification

- Re-ran the memory graph, agent node, and agent graph tests after the implementation landed.
- Confirmed `GraphMemoryStore` still loads, scores, and links turn nodes correctly, and `load_memory_context()` continues to pass query-aware context.
- Confirmed the full project test suite and Python compilation checks still pass after the memory work.
- The repo still carries a warning from FastAPI/Starlette about `httpx` deprecation, but it does not block the current work.

## 2026-07-11 PyQt C60 Logo Crash

- Reproduced the visual workbench flash-close with a subprocess smoke test that calls `MainWindow.show()` under Qt offscreen mode.
- Isolated the crash to the custom `C60Logo.paintEvent()` QPainter drawing path; regular Qt widgets and stylesheets did not crash.
- Replaced the custom-painted logo with a styled `QFrame`/`QLabel` logo and kept a smoke test so future visual changes must survive real show/process-events startup.

## 2026-07-11 Brand Image Asset

- Processed the desktop `c.png` into `src/copy_myself/gui/assets/brand_c.png` by cropping out the lower-right AI-generated text while preserving the molecule-like brand mark.
- Updated the PyQt sidebar logo to load the bundled image asset through `QPixmap`, with a text fallback only if the asset is missing.
- Added GUI tests that verify the logo pixmap loads and that `MainWindow.show()` still survives Qt event processing.

## 2026-07-12 Provider API Settings

- Reworked the PyQt settings page around model profiles instead of preset endpoint choices.
- Kept the user-facing form to three required values: model name, Base URL, and API key.
- Added saved-profile switching so a selected model updates `.env` and the current process environment for the next chat turn.
- Persisted profiles through `config.save_model_settings()` and retained the old save helper only as a compatibility wrapper.
- Updated README and architecture documentation to describe GUI-based model configuration and switching.
- Verified with `python -m pytest tests\gui tests\test_config.py -v`, `python -m pytest -v`, and `python -m compileall -q src tests`.

## 2026-07-12 GUI Workbench Redesign

- Adopted the approved simple three-column PyQt layout: left C60 rail, center chat, and right execution inspector.
- Added visible inspector sections for execution stages, plan list, local tool catalog, external MCP status, current intent, and latest tool result.
- Moved complete memory out of the always-visible inspector; it now opens only through the `完整记忆` button.
- Added GUI regression tests for the new structure and memory dialog behavior.
- Verified with `python -m pytest -v` and `python -m compileall -q src tests`; pytest still reports the existing Starlette/httpx deprecation warning.
- Follow-up adjustment: removed visible C60 naming, simplified the left rail to `工作台` / `记忆` / `设置`, removed the right-side tool-result panel, and restored a dark sci-fi visual treatment.

## 2026-07-12 MCP Service Import

- Added a simple PyQt settings card for importing external MCP services by name plus startup command or URL.
- Persisted imported services to `.env` as `COPY_MYSELF_MCP_SERVICES`.
- Refreshed the right-side available tools panel so imported MCP services appear beside built-in tools.
- Kept external MCP process startup behind the existing adapter boundary instead of launching services directly from widgets.

## 2026-07-12 Active Model Display Fix

- Traced a model display mismatch to `load_settings()` letting legacy `COPY_MYSELF_MODEL_NAME` override the active model profile.
- Changed active profile precedence so the settings page and agent responder resolve the same current model.
- Added regression coverage for active-profile precedence and GUI current-model display.

## 2026-07-12 Premium Sci-Fi Blue Theme

- Upgraded the PyQt workbench stylesheet to a deeper gradient sci-fi blue visual style.
- Added regression coverage so the theme keeps key gradient and accent colors.
- Kept the existing layout and behavior unchanged while improving perceived polish.

## 2026-07-12 Project Cleanup And README Rewrite

- Rewrote `README.md` in Chinese around the current PyQt-first runtime, CLI/API entry points, model settings, memory files, MCP import, repository hygiene, and verification commands.
- Updated `.gitignore` so local secrets such as `keys` remain ignored while root Markdown files are no longer broadly ignored.
- Refreshed `.env.example` for the current model profile and MCP settings, and removed the retired Vite frontend variable.
- Removed local generated artifacts where Windows permissions allowed it: `.idea/`, `memory/`, `src/copy_myself.egg-info/`, and Python `__pycache__/` directories.
- `.pytest_cache/` remained undeleted because Windows returned `Access is denied`; it is still ignored by git.

## 2026-07-12 PyQt Page Switch Size Fix

- Reproduced the workbench resize bug under Qt offscreen: switching to settings changed the window from `1240x780` to `1240x852`, then switching back grew it to `1240x1070`.
- Traced the root cause to the settings page `minimumSizeHint`; its full form height forced the top-level window minimum height upward during show/hide navigation.
- Wrapped the settings page in a widget-resizable `QScrollArea` so long settings content scrolls inside the center panel instead of resizing the main window.
- Added a GUI regression test that clicks Settings and Workbench and asserts the main window size stays unchanged.

## 2026-07-10 C60 Sci-Fi GUI

- Restyled the PyQt workbench as a dark sci-fi command console with cyan, violet, and magenta accents.
- Added a custom painted `C60Logo` widget as the assistant's signature mark and updated visible UI copy around the C60 identity.
- Preserved existing GUI behavior: streaming responses, new conversation reset, long-message sizing, complete-memory display, and memory flush on close.
- Added GUI coverage to assert the C60 identity exists in the main window.
- Verified with `python -m pytest -v` and `python -m compileall -q src tests`. Screenshot capture was blocked by the local Qt platform layer in this execution environment.
