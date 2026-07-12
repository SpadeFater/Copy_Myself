# Memory Graph Design

## Goal

Copy_Myself should evolve from message-level durable memory into a local-first memory graph. Each completed user-assistant turn becomes a durable memory node that preserves the raw exchange, extracts structured long-term memory, and links to related nodes for future retrieval.

## Product Behavior

- Every completed interaction can be saved as one `MemoryNode`.
- A node keeps the raw question and answer, plus structured memory buckets:
  - `preference_memory`: user communication style, habits, and durable preferences.
  - `project_memory`: project facts, architecture decisions, constraints, and direction.
  - `task_memory`: active tasks, milestones, status, and next actions.
  - `episode_memory`: what happened in this exchange and how it was handled.
- Memory remains permanently local under the project `memory/` folder.
- Agent runs retrieve a small, ranked memory context instead of depending on the current chat window.
- The system stays usable without API keys by using deterministic local extraction, scoring, and composition.

## Architecture

Add a graph memory store beside the existing persistent message store. `PersistentMemoryStore` remains compatible with current complete-memory JSONL files but is display-only and returns no model context. `GraphMemoryStore` stores nodes and edges in SQLite, implements the graph-facing `MemoryStore` boundary, and adds turn-level persistence through `save_turn()`.

The LangGraph `load_memory_context` node uses graph memory context composition for model-facing memory. For graph memory, that context is dynamically composed from the most relevant nodes for the current request.

## Storage

The first graph implementation stores data in:

```text
memory/
  memory_graph.sqlite3
  full_memory.jsonl
  sessions/
```

SQLite tables:

- `memory_nodes`: raw turn, structured memory buckets, tags, project, task id, importance, confidence, optional embedding JSON, and source.
- `memory_edges`: related-node edges with relation, weight, reason, and timestamp.

`memory_revisions` is intentionally deferred until editable memory is introduced.

## Retrieval

For each user request, graph memory should:

1. Analyze the query with deterministic local rules.
2. Search candidate nodes by keyword overlap, tags, project, task fields, and recent activity.
3. Expand through strong edges such as `same_task`, `same_project`, and `preference_related`.
4. Score candidates using relevance, importance, recency, confidence, and edge weight.
5. Compose the top nodes into a compact model-facing context grouped by preference, project, task, and episode memory.

The first implementation may use token overlap and rule-based extraction. Embeddings are optional and can be added later without changing the storage contract.

## GUI

The PyQt workbench should continue to list complete memory through the view model. For graph memory, recent items should display node summaries while future GUI slices can show node details, related nodes, and why a node was recalled.

## Testing

Tests should cover SQLite persistence, structured extraction, edge creation, retrieval composition, agent `save_turn()` integration, and view-model memory listing.

Verification remains:

```powershell
python -m pytest -v
python -m compileall -q src tests
```
