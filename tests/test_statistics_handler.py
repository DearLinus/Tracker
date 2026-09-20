import pytest

from logic import TrackerLogic


# The original handler tests depended on Telegram Update/Context and
# monkeypatching tracker.get_records. These tests exercise the
# statistics calculation logic directly by calling TrackerLogic.get_statistics.
# This makes them faster, simpler, and independent from handler plumbing.


def test_statistics_without_records(monkeypatch):
    logic = TrackerLogic(db_path=":memory:")

    # Stub out get_records to avoid touching the DB and to isolate the
    # behavior under test.
    monkeypatch.setattr(logic, "get_records", lambda user_id: {})

    stats = logic.get_statistics(123)

    assert stats == {
        "days": 0,
        "total": 0,
        "average": 0,
        "highest": 0,
    }


def test_statistics_calculates_values(monkeypatch):
    logic = TrackerLogic(db_path=":memory:")

    monkeypatch.setattr(
        logic,
        "get_records",
        lambda user_id: {
            # use ints as values; keys can be dates or strings - only values()
            # are used by the calculation
            "2026-09-10": 5,
            "2026-09-11": 10,
            "2026-09-12": 15,
        },
    )

    stats = logic.get_statistics(123)

    assert stats["days"] == 3
    assert stats["total"] == 30
    assert pytest.approx(stats["average"], rel=1e-9) == 10.0
    assert stats["highest"] == 15


def test_statistics_uses_correct_user_id(monkeypatch):
    logic = TrackerLogic(db_path=":memory:")

    received_ids = []

    def fake_get_records(user_id):
        received_ids.append(user_id)
        return {"2026-09-10": 5}

    monkeypatch.setattr(logic, "get_records", fake_get_records)

    _ = logic.get_statistics(123)

    assert received_ids == [123]
