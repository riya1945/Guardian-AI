from __future__ import annotations

from fastapi.testclient import TestClient

from regret_engine.api.main import app
from regret_engine.src.regret_service import load_demo_decisions


client = TestClient(app)


def _decision_payload(decision_id: str = "test-api-001") -> dict[str, object]:
    decision = load_demo_decisions(limit=1)[0]
    payload = decision.model_dump() if hasattr(decision, "model_dump") else decision.dict()
    payload["decision_id"] = decision_id
    return payload


def test_health_reports_model_and_rag() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["model_loaded"] is True
    assert body["rag_chunks"] > 0
    assert body["storage_backend"] in {"memory", "exasol"}
    assert body["vector_backend"] in {"memory_vectors", "exasol_python_vectors"}
    assert body["embedding_provider"] in {"hash", "gemini"}
    assert body["llm_chain"]


def test_legacy_regret_endpoint_still_returns_original_shape() -> None:
    response = client.post("/calculate-regret", json=_decision_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "INR"
    assert "regret" in body
    assert "decision_quality" in body
    assert "alternatives" not in body


def test_decision_endpoint_returns_grounded_record() -> None:
    response = client.post("/decision", json=_decision_payload("test-api-structured"))

    assert response.status_code == 200
    body = response.json()
    assert body["decision_id"] == "test-api-structured"
    assert body["explanation"]["status"] == "grounded"
    assert body["explanation"]["supporting_evidence"]
    assert body["factors"]


def test_decision_feed_analytics_and_dashboard_routes() -> None:
    decisions_response = client.get("/decisions?limit=5")
    analytics_response = client.get("/analytics")
    dashboard_response = client.get("/dashboard")

    assert decisions_response.status_code == 200
    assert len(decisions_response.json()) <= 5
    assert analytics_response.status_code == 200
    assert analytics_response.json()["total_decisions"] > 0
    assert dashboard_response.status_code == 200
    assert "Pricing Regret Console" in dashboard_response.text


def test_explain_refuses_unrelated_question() -> None:
    decision_id = client.get("/decisions?limit=1").json()[0]["decision_id"]
    response = client.post(
        f"/explain/{decision_id}",
        json={"question": "who won the tennis final", "top_k": 3},
    )

    assert response.status_code == 200
    explanation = response.json()["explanation"]
    assert explanation["status"] == "insufficient_evidence"
    assert "Evidence unavailable" in explanation["summary"]
