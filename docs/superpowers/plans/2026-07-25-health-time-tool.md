# Health Tool Current-Time Milestone

## Goal

Repurpose the old `health` tool into the `getTime` time tool while keeping the
LangGraph tool boundary stable.

## Scope

- Accept an IANA `timezone` or a supported `location`.
- Return structured time and timezone data.
- Route natural-language time requests through the agent.
- Keep invalid timezone input as a structured tool error.

## Verification

- Add focused tool and agent tests first.
- Run `python -m pytest -v`.
- Run `python -m compileall -q src tests`.
