from __future__ import annotations

from regret_engine.src.rag_explainer import RagExplainer, evaluate_explainer
from regret_engine.src.regret_service import RegretService, load_demo_decisions


def test_retriever_preserves_source_metadata() -> None:
    explainer = RagExplainer()
    evidence = explainer.vector_store.retrieve(
        "counterfactual price regret risk evidence",
        top_k=3,
    )

    assert evidence
    assert evidence[0].source.endswith("#chunk-1") or "#chunk-" in evidence[0].source
    assert evidence[0].title
    assert evidence[0].relevance_score > 0


def test_explanation_is_grounded_in_retrieved_evidence() -> None:
    service = RegretService()
    explainer = RagExplainer()
    record = service.build_record(load_demo_decisions(limit=1)[0])

    explanation = explainer.explain(record)

    assert explanation.status == "grounded"
    assert explanation.supporting_evidence
    assert explanation.key_factors
    assert str(round(record.regret.regret, 2)) in explanation.explanation


def test_unrelated_question_returns_refusal() -> None:
    service = RegretService()
    explainer = RagExplainer()
    record = service.build_record(load_demo_decisions(limit=1)[0])

    explanation = explainer.explain(
        record,
        question="who won the tennis final",
    )

    assert explanation.status == "insufficient_evidence"
    assert explanation.supporting_evidence == []
    assert explanation.summary == "This information is not found in the uploaded documents"


def test_rag_evaluation_is_deterministic() -> None:
    explainer = RagExplainer()
    result = evaluate_explainer(explainer)

    assert result["evaluation_source"] == "gold_eval"
    assert result["gold_queries"] == 30
    assert result["passed"] >= 25
    assert result["failure_rate"] <= 0.17
