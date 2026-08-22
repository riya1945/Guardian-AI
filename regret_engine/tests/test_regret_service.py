from __future__ import annotations

from regret_engine.src.regret_service import RegretService, load_demo_decisions


def test_structured_record_contains_counterfactual_trace() -> None:
    service = RegretService()
    decision = load_demo_decisions(limit=1)[0]

    record = service.build_record(decision)

    assert record.decision_id == decision.decision_id
    assert record.regret.alternatives
    assert any(item.is_selected for item in record.regret.alternatives)
    assert any(item.is_best for item in record.regret.alternatives)
    assert record.factors
    assert record.assumptions


def test_candidate_prices_include_actual_price() -> None:
    service = RegretService()
    prices = service.generate_candidate_prices(100.0)

    assert 100.0 in prices
    assert prices.min() == 90.0
    assert prices.max() == 110.0
