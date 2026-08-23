from __future__ import annotations

import json
from pathlib import Path

from regret_engine.src.rag_explainer import load_gold_eval_cases, load_knowledge_chunks
from regret_engine.src.regret_service import RegretService, load_demo_decisions
from regret_engine.src.schemas import Decision


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CONTRACT_FILE = BASE_DIR.parent / "contracts" / "decision_contract.md"


def test_provided_knowledge_corpus_contains_required_policy_sources() -> None:
    required_files = {
        "pricing_policy.md",
        "guardrail_rules.md",
        "incident_reports.md",
        "review_sop.md",
        "escalation_rules.md",
        "business_constraints.md",
        "decision_examples.md",
    }
    actual_files = {path.name for path in KNOWLEDGE_DIR.glob("*.md")}
    assert required_files.issubset(actual_files)

    corpus_text = "\n".join(path.read_text(encoding="utf-8") for path in KNOWLEDGE_DIR.glob("*.md"))
    for source_id in ["PP-002", "GR-001", "GR-007", "SOP-004", "ESC-003", "BC-007", "INC-2026-003", "DEC-010"]:
        assert source_id in corpus_text

    chunks = load_knowledge_chunks(KNOWLEDGE_DIR)
    assert len(chunks) >= 30


def test_mock_decisions_validate_against_decision_schema() -> None:
    decisions = load_demo_decisions(limit=50)

    assert len(decisions) == 40
    assert all(isinstance(decision, Decision) for decision in decisions)
    assert {decision.decision_id for decision in decisions} >= {"dec_0001", "dec_0038", "dec_0040"}


def test_gold_eval_contract_and_refusal_cases() -> None:
    cases = load_gold_eval_cases(DATA_DIR / "gold_eval.json")

    assert len(cases) == 30
    refusal_cases = [case for case in cases if case["should_refuse"]]
    grounded_cases = [case for case in cases if not case["should_refuse"]]
    assert len(refusal_cases) == 5
    assert len(grounded_cases) == 25
    assert all(case["expected_sources"] for case in grounded_cases)
    assert all(case["expected_sources"] == [] for case in refusal_cases)


def test_decision_labels_match_mock_decision_ids() -> None:
    decisions = json.loads((DATA_DIR / "mock_decisions.json").read_text(encoding="utf-8"))
    labels = json.loads((DATA_DIR / "decision_labels.json").read_text(encoding="utf-8"))

    decision_ids = {item["decision_id"] for item in decisions}
    label_ids = {item["decision_id"] for item in labels}
    assert decision_ids == label_ids
    assert {item["risk_level"] for item in labels} == {"LOW", "MEDIUM", "HIGH"}


def test_decision_labels_drive_demo_guardrail_context() -> None:
    service = RegretService()
    decision = next(
        decision
        for decision in load_demo_decisions(limit=40)
        if decision.decision_id == "dec_0009"
    )

    record = service.build_record(decision)

    assert record.risk_level == "HIGH"
    assert record.regret.best_price == 503
    assert record.regret.regret == 21445
    assert record.recommendation == "Escalate guardrail decision before release"
    assert any(factor.factor == "Guardrail GR-003" for factor in record.factors)


def test_contract_document_lists_api_payload_shapes() -> None:
    contract = CONTRACT_FILE.read_text(encoding="utf-8")

    for section in ["Decision Input", "Regret Output", "Explanation Output", "Dashboard Feed Item"]:
        assert section in contract
