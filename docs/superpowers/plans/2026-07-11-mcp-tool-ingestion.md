# MCP Tool Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Copy_Myself consume every tool through an MCP-style service boundary, while still letting local tools be authored as simple Python modules and external MCP services be attached through configuration.

**Architecture:** Introduce a small MCP-oriented tool layer that treats local tools and external services the same way at the agent boundary. Local tool modules are exposed through a built-in local MCP source, external services are exposed through configurable MCP client sources, and the agent only sees normalized tool catalogs and tool executions. Keep tool discovery, transport details, and source composition out of `agent/nodes.py`.

**Tech Stack:** Python dataclasses, `typing.Protocol`, pytest, existing local tool modules, project config loading, and a lightweight MCP adapter layer implemented inside `src/copy_myself/tools/`.

---

### Task 1: Define The MCP Tool Boundary

**Files:**
- Modify: `src/copy_myself/tools/base.py`
- Modify: `src/copy_myself/tools/__init__.py`
- Modify: `tests/tools/test_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
from copy_myself.tools import LocalTool, ToolRegistry, ToolResult


class ExampleTool(LocalTool):
    name = "example"
    description = "Example tool."

    def run(self, arguments):
        return ToolResult(name=self.name, ok=True, data={"value": arguments["value"]})


def test_local_tool_can_still_be_written_as_a_plain_python_class():
    registry = ToolRegistry(discover=False)
    registry.register(ExampleTool())

    result = registry.run("example", {"value": 7})

    assert result.ok is True
    assert result.data == {"value": 7}
```

- [ ] **Step 2: Run the test to verify the current API shape is covered**

Run: `python -m pytest tests/tools/test_registry.py -v`
Expected: PASS once the `LocalTool` base class and exports are in place.

- [ ] **Step 3: Implement the boundary types**

```python
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Tool(Protocol):
    name: str
    description: str

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        """Run the tool with structured arguments."""


class LocalTool(ABC):
    name: str
    description: str
```

- [ ] **Step 4: Run the test again**

Run: `python -m pytest tests/tools/test_registry.py -v`
Expected: PASS.

### Task 2: Add MCP Source Composition

**Files:**
- Create: `src/copy_myself/tools/mcp.py`
- Modify: `src/copy_myself/tools/registry.py`
- Modify: `tests/tools/test_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
from dataclasses import dataclass

from copy_myself.tools import ToolRegistry, ToolResult
from copy_myself.tools.registry import ToolSource


@dataclass
class ExternalTool:
    name: str = "external"
    description: str = "External MCP tool."

    def run(self, arguments):
        return ToolResult(name=self.name, ok=True, data={"value": arguments.get("value")})


class ExternalSource(ToolSource):
    def list_tools(self):
        return [ExternalTool()]


def test_registry_can_load_a_tool_source():
    registry = ToolRegistry(discover=False)
    registry.load_source(ExternalSource())

    assert registry.names() == ["external"]
    assert registry.run("external", {"value": 11}).data == {"value": 11}
```

- [ ] **Step 2: Run the test to verify it fails before implementation**

Run: `python -m pytest tests/tools/test_registry.py -v`
Expected: FAIL until `ToolSource` and source loading are implemented.

- [ ] **Step 3: Implement source composition and a service-shaped adapter**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from copy_myself.tools.base import Tool


class ToolSource(Protocol):
    def list_tools(self) -> list[Tool]:
        """Return tools exposed by one MCP service or MCP-compatible source."""


@dataclass(frozen=True)
class ToolCatalogItem:
    name: str
    description: str


class ToolExecutionSource(Protocol):
    def list_catalog(self) -> list[ToolCatalogItem]:
        ...

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        ...
```

- [ ] **Step 4: Run the test again**

Run: `python -m pytest tests/tools/test_registry.py -v`
Expected: PASS.

### Task 3: Make The Agent Consume Only The MCP Boundary

**Files:**
- Modify: `src/copy_myself/agent/graph.py`
- Modify: `src/copy_myself/agent/nodes.py`
- Modify: `tests/agent/test_graph.py`

- [ ] **Step 1: Write the failing test**

```python
from copy_myself.agent.graph import build_default_registry


def test_default_registry_still_exposes_local_mcp_tools():
    registry = build_default_registry()

    assert "health" in registry.names()
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/agent/test_graph.py -v`
Expected: PASS after the agent no longer hard-codes specific tool registration.

- [ ] **Step 3: Update the agent to stay source-agnostic**

```python
from copy_myself.tools import ToolRegistry


def build_default_registry() -> ToolRegistry:
    return ToolRegistry(discover=True)
```

- [ ] **Step 4: Run the agent tests**

Run: `python -m pytest tests/agent/test_graph.py -v`
Expected: PASS.

### Task 4: Document How To Author Local And External MCP Tools

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Add usage docs**

Explain that local tools live under `src/copy_myself/tools/`, that they are discovered automatically, and that external services are attached through MCP sources loaded by the registry.

- [ ] **Step 2: Add verification commands**

Run: `python -m pytest -v`
Run: `python -m compileall -q src tests`
Expected: both pass.

### Task 5: Full Verification

**Files:**
- All files above.

- [ ] **Step 1: Run focused tool tests**

Run: `python -m pytest tests/tools/test_registry.py -v`
Expected: PASS.

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -v`
Expected: PASS.

- [ ] **Step 3: Run compilation checks**

Run: `python -m compileall -q src tests`
Expected: PASS.
