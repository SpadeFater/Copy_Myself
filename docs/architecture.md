# Architecture

## Purpose

Copy_Myself is designed as a personal butler agent. The foundation keeps core orchestration separate from concrete abilities so the project can grow without rewriting its center.

## LangGraph Flow

```text
load_memory -> classify_intent -> run_tool -> create_response -> END
```

## PyQt Workbench Shape

The target product shape is a PyQt desktop personal-butler dashboard combined with a Codex-style execution panel:

- Left rail: workspaces, conversations, memory, and settings.
- Center: today overview, primary chat, and streaming agent responses.
- Right inspector: graph execution steps, tool results, and complete memory for user inspection.

The first PyQt version is intentionally a shell. It calls the agent through a GUI view model and leaves concrete butler abilities for later feature slices. The desktop path uses `stream_agent` so model output can be appended to the pending assistant message as chunks arrive, while CLI and API paths can keep using `run_agent`.

The PyQt settings page owns interactive model profile configuration. The user
only provides a model name, Base URL, and API key. Saved profiles are listed in
a model switcher, and choosing a different profile updates `.env` plus the
current process environment so the next chat turn uses that model immediately.
The model adapter still reads configuration through `config.py`, keeping
external API details outside graph nodes and widgets.

## API Layer

FastAPI exposes the agent to integrations and optional non-desktop surfaces. It is not the primary GUI runtime; the PyQt workbench calls the agent directly:

- `GET /api/status`: health and surface metadata.
- `POST /api/chat`: runs the LangGraph agent for one message and returns response, intent, tool result, memory context, and session id.

The API owns session-level memory through `SessionStore`. This keeps the CLI simple while allowing HTTP clients to preserve short-lived context.

## State

`ButlerState` is the shared graph contract. It carries the user input, message history, detected intent, selected tool, tool result, memory context, response, and error.

## Tools

Tools enter the agent through an MCP-style source boundary. Local Python tools are exposed by `LocalToolSource`, and external MCP services can be adapted through `McpToolSource`. The graph only calls `ToolRegistry`, so agent nodes do not need to know whether a tool came from local code or an external service.

Local tools implement a small protocol:

- `name`
- `description`
- `run(arguments)`

`ToolRegistry` owns source loading, catalog listing, and execution. During `classify_intent`, the current tool catalog is passed to the configured model adapter and the model returns a JSON tool choice with arguments. Missing, invalid, or failing tool choices fall back to chat or structured tool errors instead of crashing the graph.

## Memory

Memory is represented by a protocol with message-level `save`, turn-level `save_turn`, search, node retrieval, recent listing, and query-aware context composition. `InMemoryStore` remains suitable for tests and short-lived API sessions. `PersistentMemoryStore` remains available only as a display/archive layer for the retired JSONL memory format. `GraphMemoryStore` is the PyQt workbench default and writes local runtime memory under `memory/`.

- `full_memory.jsonl`: complete memory records for user inspection.
- `sessions/<session_id>.jsonl`: per-session conversation records.
- `memory_graph.sqlite3`: graph memory nodes and relation edges.

Graph memory saves each completed user-assistant exchange as one node. Each node preserves the raw turn and extracts preference, project, task, and episode memory. Related nodes are linked with local relation edges such as same task, same project, semantic similarity, and preference relation. On each agent run, `load_memory_context` passes the current query to the graph memory store and receives a compact, ranked context grouped by long-term preferences, project facts, task memory, and historical process notes. The retired JSONL store returns no model context; it only supports complete-memory display. The first graph implementation uses deterministic local extraction and token scoring, so memory retrieval works without API keys.

## Extension Points

- Add new local tools under `src/copy_myself/tools` by subclassing `LocalTool` and writing a clear `description`.
- Add external tools by adapting an MCP client through `McpToolSource`.
- Replace placeholder response creation with a model adapter.
- Extend `GraphMemoryStore` with embeddings, editable memory revisions, stronger conflict handling, or LangGraph checkpointing.
- Add richer PyQt workbench states under `src/copy_myself/gui` as concrete butler abilities appear.

## Non-Goals For The Foundation

- No real calendar or reminder integration yet.
- No background scheduler yet.
- No production-grade packaging for the PyQt desktop app yet.
- No multi-user security model yet.
