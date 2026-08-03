# Contributing

## Local Setup

Install the package with development dependencies:

```powershell
python -m pip install -e .[dev]
```

If Chinese output is garbled in Windows PowerShell, switch the session to UTF-8:

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

## Verification

Run these before reporting backend or GUI logic complete:

```powershell
python -m pytest -v
python -m compileall -q .
```

For PyQt GUI changes, also launch the desktop workbench after `PyQt6` is installed:

```powershell
copy-myself-gui
```

Do not mark GUI startup verified unless the window launches successfully.

## Development Rules

- Keep LangGraph as the orchestration boundary.
- Keep PyQt widgets under `gui/`.
- Keep testable GUI state in non-widget modules such as `gui/view_model.py`.
- Route API, GUI, and CLI chat flows through `agent.service.ChatService`.
- Keep runtime SQLite data under `memoryGraphData/`, outside the `memory/` code package.
- Keep external API calls behind adapters and out of graph nodes, widgets, and tests.
- Start each milestone from a focused plan in `docs/superpowers/plans/`.
- Prefer small, focused changes that follow the existing package structure.

## Git Hygiene

- Do not commit virtual environments, caches, build outputs, `.env` files, or local IDE state.
- Commit after coherent milestones once verification passes.
- Do not revert or overwrite unrelated user changes.
