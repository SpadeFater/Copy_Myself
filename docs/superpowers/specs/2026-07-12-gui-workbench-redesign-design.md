# GUI Workbench Redesign Design

## Goal

Replan the PyQt workbench around a simple three-column dashboard: logo and navigation on the left, chat in the center, and execution visibility on the right.

## Chosen Layout

Use the recommended three-column workbench.

- Left rail: Copy_Myself logo/name in the top-left, then exactly three buttons: "工作台", "记忆", and "设置".
- Center: chat title, conversation list, and input composer.
- Right inspector: execution stage list, plan list, available tools, and current intent.

## Behavior

- Memory is not shown by default in the main inspector.
- Clicking "记忆" opens a focused complete-memory viewer dialog populated from `WorkbenchViewModel.complete_memory_items()`.
- Available tools show the local registry catalog and a clear external MCP placeholder when no external MCP source is attached.
- Execution stages remain based on the LangGraph node order already exposed by `RunSummary.graph_steps`.
- Plan list is lightweight GUI state for now: it shows standby/default items before a run and run-derived items after completion.
- Settings stay available from the left rail and keep the existing model profile form.
- Tool results are no longer shown in the right inspector; they remain in the run summary/state for tests and future detail views.
- The visual style returns to a dark sci-fi workbench, but visible C60 naming is removed.

## Boundaries

- Keep LangGraph orchestration unchanged.
- Keep GUI code under `src/copy_myself/gui/`.
- Use existing `ToolRegistry.catalog()` instead of inventing a separate tool system.
- Do not make external MCP calls directly from widgets; the GUI only displays catalog/source status.

## Testing

- Add GUI tests for visible logo, tool catalog panel, execution stages, plan list, hidden-by-default memory, memory button/dialog, and settings entry.
- Run the full project verification commands:
  - `python -m pytest -v`
  - `python -m compileall -q src tests`
