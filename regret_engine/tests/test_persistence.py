from __future__ import annotations

from regret_engine.src.persistence import InMemoryDecisionRepository
from regret_engine.src.regret_service import RegretService, load_demo_decisions


def test_in_memory_repository_round_trips_decision_record() -> None:
    service = RegretService()
    repository = InMemoryDecisionRepository()
    record = service.build_record(load_demo_decisions(limit=1)[0])

    repository.save(record)

    assert repository.count() == 1
    assert repository.get(record.decision_id) == record
    assert repository.list_records(limit=10)[0] == record
