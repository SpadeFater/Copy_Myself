from fastapi.testclient import TestClient

from copy_myself.api.app import create_app


def test_chat_endpoint_runs_agent() -> None:
    client = TestClient(create_app())

    response = client.post("/api/chat", json={"message": "health check"})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "health check"
    assert body["intent"] == "health_check"
    assert body["tool_result"] == {"status": "ok", "source": "agent"}
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
