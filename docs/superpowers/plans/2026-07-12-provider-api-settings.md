# Model API Settings Plan

## Goal

Add a PyQt settings surface where the user can manually configure model API details without editing `.env` by hand.

## Scope

- Let the user provide only model name, Base URL, and API key.
- Persist saved model profiles to the project `.env`.
- Add a model switcher that can activate any saved profile.
- Update the running process environment after save or switch so the next message uses the active model settings.
- Keep the model adapter behind the existing OpenAI-compatible responder boundary.
- Add tests for config persistence and GUI settings controls.

## Verification

- `python -m pytest -v`
- `python -m compileall -q src tests`
