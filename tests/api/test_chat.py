from datetime import datetime

from fastapi.testclient import TestClient

from api.app import create_app


def test_chat_endpoint_runs_agent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COPY_MYSELF_MEMORY_PATH", str(tmp_path / "memory.sqlite3"))
    client = TestClient(create_app())

    response = client.post("/api/chat", json={"message": "what time is it in UTC?"})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "what time is it in UTC?"
    assert body["intent"] == "time_lookup"
    assert body["tool_result"]["status"] == "ok"
    assert body["tool_result"]["source"] == "agent"
    assert body["tool_result"]["timezone"]
    assert datetime.fromisoformat(body["tool_result"]["time"]).tzinfo is not None
    assert body["response"]


def test_status_endpoint_exposes_shell_regions() -> None:
    client = TestClient(create_app())

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Copy_Myself",
        "surface": "personal-butler-workbench",
        "status": "ok",
    }
