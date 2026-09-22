from datetime import datetime, timedelta, timezone

from logic import TrackerLogic


def test_rate_limit_allows_requests_within_limit(tmp_path):
    db_path = str(tmp_path / "rate_limit.db")
    tracker = TrackerLogic(db_path=db_path)
    tracker.create_user(101)

    assert tracker.check_rate_limit(101, "graph_generation") is True
    assert tracker.check_rate_limit(101, "graph_generation") is True


def test_rate_limit_blocks_requests_after_limit_reached(tmp_path):
    db_path = str(tmp_path / "rate_limit.db")
    tracker = TrackerLogic(db_path=db_path)
    tracker.create_user(202)

    assert tracker.check_rate_limit(202, "export_generation") is True
    assert tracker.check_rate_limit(202, "export_generation") is True
    assert tracker.check_rate_limit(202, "export_generation") is False


def test_rate_limit_exact_boundary_limit_is_allowed_and_next_request_is_blocked(tmp_path):
    db_path = str(tmp_path / "rate_limit_boundary.db")
    tracker = TrackerLogic(db_path=db_path)
    tracker.create_user(303)

    for _ in range(5):
        assert tracker.check_rate_limit(303, "graph_generation") is True

    assert tracker.check_rate_limit(303, "graph_generation") is False


def test_rate_limit_window_expires_after_window_passes(tmp_path):
    db_path = str(tmp_path / "rate_limit_window.db")
    tracker = TrackerLogic(db_path=db_path)
    tracker.create_user(404)

    now = datetime.now(timezone.utc)
    assert tracker.database.check_and_record_rate_limit(404, "export_generation", 2, 60, now=now) is True
    assert tracker.database.check_and_record_rate_limit(404, "export_generation", 2, 60, now=now) is True
    assert tracker.database.check_and_record_rate_limit(404, "export_generation", 2, 60, now=now) is False

    later = now + timedelta(seconds=61)
    assert tracker.database.check_and_record_rate_limit(404, "export_generation", 2, 60, now=later) is True


def test_rate_limit_uses_fixed_window_bucket_for_same_window_requests(tmp_path):
    db_path = str(tmp_path / "fixed_window_bucket.db")
    tracker = TrackerLogic(db_path=db_path)
    tracker.create_user(444)

    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    assert tracker.database.check_and_record_rate_limit(444, "graph_generation", 2, 60, now=base + timedelta(seconds=5)) is True
    assert tracker.database.check_and_record_rate_limit(444, "graph_generation", 2, 60, now=base + timedelta(seconds=30)) is True
    assert tracker.database.check_and_record_rate_limit(444, "graph_generation", 2, 60, now=base + timedelta(seconds=59)) is False


def test_rate_limit_tracks_graph_and_export_separately(tmp_path):
    db_path = str(tmp_path / "rate_limit_separate.db")
    tracker = TrackerLogic(db_path=db_path)
    tracker.create_user(505)

    for _ in range(2):
        assert tracker.check_rate_limit(505, "export_generation") is True

    assert tracker.check_rate_limit(505, "export_generation") is False

    for _ in range(5):
        assert tracker.check_rate_limit(505, "graph_generation") is True

    assert tracker.check_rate_limit(505, "graph_generation") is False
