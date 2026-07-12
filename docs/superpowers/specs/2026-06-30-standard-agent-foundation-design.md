# Copy_Myself Standard Agent Foundation Design

## Goal

Build a standard development foundation for Copy_Myself, a personal butler agent based on LangGraph. The foundation should be runnable, testable, and easy to extend without locking the project into specific calendar, reminder, or note-taking implementations too early.

## Scope

This foundation includes:

- A Python package under `src/copy_myself`.
- A LangGraph workflow with focused state, node, routing, and graph modules.
- A command-line entry point for local interaction.
- A tool abstraction with one sample tool.
- A memory abstraction with an in-memory implementation.
- Configuration, logging, and project metadata.
- Tests covering the initial graph, memory, tool, and CLI behavior.
- README and architecture documentation.

This foundation does not include:

- Real calendar, reminder, email, or note integrations.
- Real long-term vector memory.
- Background scheduling.
- Browser-hosted GUI.
- Multi-user authentication.

## Architecture

The agent is organized around a small LangGraph state machine. User input enters the graph, is inspected by an intent node, may be routed to a tool node, and then reaches a response node. Errors are captured in state and turned into a graceful response.

The first version keeps LLM calls behind placeholder logic so the project can run without API keys. Future model integrations can replace the intent and response nodes without changing the graph boundary.

## Components

- `copy_myself.agent.state`: Typed state shared across graph nodes.
- `copy_myself.agent.nodes`: Pure node functions that transform state.
- `copy_myself.agent.graph`: Graph construction and invocation helpers.
- `copy_myself.tools`: Tool protocol, registry, and sample health tool.
- `copy_myself.memory`: Memory protocol and in-memory implementation.
- `copy_myself.config`: Environment-driven settings.
- `copy_myself.logging`: Logging setup.
- `copy_myself.cli`: Local command-line interface.

## Data Flow

1. The CLI receives user input.
2. `run_agent` creates the initial state.
3. The graph classifies the request.
4. Requests that look like health checks call the sample tool.
5. All requests reach the response node.
6. The response node stores a short interaction record in memory.
7. The CLI prints the final assistant response.

## Error Handling

Tool failures and unexpected node failures should be represented in the shared state with an `error` field. The response node should turn the error into a user-facing fallback message instead of crashing normal interactions.

## Testing

Tests should verify:

- State defaults are predictable.
- Memory can save and retrieve interaction snippets.
- Tool registry can register and execute tools.
- Graph invocation returns a response for normal input.
- Health-check input routes through the sample tool.
- CLI formatting is stable enough for local use.

## Implementation Constraints

- Keep the first version dependency-light.
- Use LangGraph as the orchestration boundary.
- Avoid real external API calls in tests.
- Keep concrete personal-butler features behind interfaces until their requirements are clearer.
