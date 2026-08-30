from pathlib import Path

from fastapi.testclient import TestClient

from x2video.api.app import create_app


def test_api_run_gate_and_snapshot(tmp_path: Path) -> None:
    app = create_app(work_dir=str(tmp_path / "work"), db_path=str(tmp_path / "agent.db"))
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    created = client.post(
        "/api/runs",
        json={"query": "今日 AI 圈三件事", "autonomy": "assisted"},
    )
    assert created.status_code == 201
    run_id = created.json()["run"]["run_id"]

    started = client.post(f"/api/runs/{run_id}/start", json={"background": False})
    assert started.status_code == 200
    assert started.json()["run"]["state"] == "WAIT_GATE_2"
    assert started.json()["documents"]["publish_kit/qc.after.json"]["ok"] is True

    approved = client.post(
        f"/api/runs/{run_id}/actions",
        json={"action": "approve_gate", "payload": {"summary": "审片通过"}},
    )
    assert approved.status_code == 200
    completed = client.post(f"/api/runs/{run_id}/start", json={"background": False})
    assert completed.json()["run"]["state"] == "COMPLETE"

    listing = client.get("/api/runs").json()["items"]
    assert listing[0]["run_id"] == run_id

    feedback = client.post(
        f"/api/runs/{run_id}/feedback",
        json={"category": "preference", "comment": "以后优先保留有公开评测集的消息", "rating": 5},
    )
    assert feedback.status_code == 201
    memory_id = feedback.json()["memory_id"]
    pending = client.get("/api/memories", params={"status": "pending"}).json()["items"]
    assert pending[0]["memory_id"] == memory_id
    assert client.post(f"/api/memories/{memory_id}", json={"status": "approved"}).status_code == 200

    next_run = client.post("/api/runs", json={"query": "下一条 AI 新闻"}).json()
    assert next_run["goal"]["memory_context"] == ["以后优先保留有公开评测集的消息"]
    assert client.get(f"/api/runs/{run_id}/replay").json()["event_count"] > 0


def test_api_rejects_unknown_action(tmp_path: Path) -> None:
    app = create_app(work_dir=str(tmp_path / "work"), db_path=str(tmp_path / "agent.db"))
    client = TestClient(app)
    run_id = client.post("/api/runs", json={"query": "test"}).json()["run"]["run_id"]
    response = client.post(
        f"/api/runs/{run_id}/actions",
        json={"action": "pretend_success", "payload": {}},
    )
    assert response.status_code == 409


def test_packaged_studio_supports_client_side_routes(tmp_path: Path) -> None:
    app = create_app(work_dir=str(tmp_path / "work"), db_path=str(tmp_path / "agent.db"))
    client = TestClient(app)

    assert client.get("/").status_code == 200
    route = client.get("/runs/client-side-route")
    assert route.status_code == 200
    assert '<div id="root"></div>' in route.text
