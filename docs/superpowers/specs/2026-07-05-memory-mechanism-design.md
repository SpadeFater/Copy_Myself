# Memory Mechanism Design

> Retired on 2026-07-10: this two-layer complete/brief memory mechanism no longer feeds model context. Keep the complete JSONL records only for user inspection and archive display. Use `GraphMemoryStore` for current model-facing memory retrieval.

## Goal

Copy_Myself needs a two-layer memory system: complete memory for the user to inspect, and brief memory for the model to receive on each run.

## Product Behavior

- Complete memory is durable and visible in the PyQt workbench.
- Brief memory is a compact summary generated from complete memory and used as the agent's `memory_context`.
- Starting a new conversation saves the current session, clears the chat surface and latest run state, and keeps durable memory available.
- Closing the desktop app saves the current session with the same persistence path.
- If model credentials exist, brief memory is produced by the configured model adapter through a summarization prompt.
- If model credentials do not exist or summarization fails, brief memory is still produced by deterministic local compression so the app remains local-first.

## Storage

The project writes memory under the workspace `memory/` folder:

- `memory/full_memory.jsonl`: one JSON record per remembered message, including `role`, `content`, `created_at`, and `session_id`.
- `memory/brief_memory.md`: compact model-facing memory.
- `memory/sessions/<session_id>.jsonl`: per-session conversation records for future replay and inspection.

## Architecture

`MemoryStore` remains the graph-facing boundary. Persistent memory extends the existing in-memory behavior with durable records, recent listing, session rotation, and flushing. The LangGraph `load_memory_context` node asks the memory store for brief context when available; simple stores still use `search`.

The PyQt view model owns session lifecycle actions. `MainWindow` exposes a new conversation button and calls `flush()` on close.

## Testing

Tests cover persistent storage, summary generation fallback, graph brief-context usage, view-model session rotation, and GUI close/new-session hooks. Full verification remains:

```powershell
python -m pytest -v
python -m compileall -q src tests
```
