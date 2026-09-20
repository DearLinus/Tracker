import pytest

from logic import TrackerLogic
from datetime import date, timedelta
from timezone import get_today

@pytest.fixture
def tracker(tmp_path):

    db_file = tmp_path / "test.db"

    logic = TrackerLogic(
        str(db_file)
    )

    yield logic


# =========================================================
# USERS
# =========================================================


def test_create_user(tracker):

    tracker.create_user(
        123,
        "tester"
    )

    assert tracker.user_exists(123)



def test_unknown_user(tracker):

    assert not tracker.user_exists(999)



def test_create_user_without_id(tracker):

    with pytest.raises(ValueError):

        tracker.create_user(None)



# =========================================================
# RECORDS
# =========================================================


def test_save_record(tracker):

    tracker.create_user(1)

    d = date(2026,9,18)

    tracker.save_record(
        1,
        d,
        5
    )

    assert tracker.get_record(
        1,
        d
    ) == 5



def test_get_records(tracker):

    tracker.create_user(1)

    tracker.save_record(
        1,
        date(2026,9,1),
        2
    )

    tracker.save_record(
        1,
        date(2026,9,2),
        4
    )


    records = tracker.get_records(1)


    assert len(records) == 2

    assert records[
        date(2026,9,1)
    ] == 2



def test_update_record(tracker):

    tracker.create_user(1)

    record_date = date(2026, 9, 1)

    tracker.save_record(
        1,
        record_date,
        5
    )

    tracker.update_record(
        1,
        record_date,
        10
    )

    assert tracker.get_record(
        1,
        record_date
    ) == 10


def test_update_record_rejects_unknown_user(tracker):

    with pytest.raises(ValueError, match="User does not exist"):

        tracker.update_record(
            999,
            date(2026, 9, 1),
            10
        )

def test_delete_record(tracker):

    tracker.create_user(1)

    d = date.today()


    tracker.save_record(
        1,
        d,
        3
    )


    assert tracker.delete_record(
        1,
        d
    )


    assert tracker.get_record(
        1,
        d
    ) is None

def test_save_record_for_unknown_user(tracker):

    with pytest.raises(ValueError):
        tracker.save_record(
            999,
            date.today(),
            5
        )

def test_future_date_is_rejected(tracker):

    tracker.create_user(1)

    future_date = get_today() + timedelta(days=1)

    with pytest.raises(ValueError):
        tracker.save_record(
            1,
            future_date,
            5
        )

# =========================================================
# VALIDATION
# =========================================================


def test_negative_count(tracker):

    tracker.create_user(1)

    with pytest.raises(ValueError):

        tracker.save_record(
            1,
            date.today(),
            -1
        )


def test_count_over_maximum_is_rejected(tracker):

    tracker.create_user(1)

    with pytest.raises(ValueError, match="1000"):
        tracker.save_record(
            1,
            date.today(),
            1001,
        )


def test_boolean_count(tracker):

    tracker.create_user(1)

    with pytest.raises(TypeError):

        tracker.save_record(
            1,
            date.today(),
            True
        )



def test_string_count(tracker):

    tracker.create_user(1)

    with pytest.raises(TypeError):

        tracker.save_record(
            1,
            date.today(),
            "5"
        )



def test_invalid_date(tracker):

    tracker.create_user(1)

    with pytest.raises(TypeError):

        tracker.save_record(
            1,
            "2026-09-18",
            5
        )

def test_invalid_user_id(tracker):

    with pytest.raises(ValueError):
        tracker.create_user(None)

# =========================================================
# STATISTICS
# =========================================================


def test_statistics(tracker):

    tracker.create_user(1)


    for d,c in [
        (date(2026,9,1),2),
        (date(2026,9,2),6),
        (date(2026,9,3),4)
    ]:
        tracker.save_record(
            1,
            d,
            c
        )


    assert tracker.get_total(1)==12

    assert tracker.get_average(1)==4

    assert tracker.get_highest(1)==6



def test_empty_statistics(tracker):

    tracker.create_user(1)


    assert tracker.get_total(1)==0

    assert tracker.get_average(1)==0

    assert tracker.get_highest(1)==0



# =========================================================
# SETTINGS
# =========================================================


def test_settings(tracker):

    tracker.create_user(1)


    tracker.set_setting(
        1,
        "graph_theme",
        "dark"
    )


    assert tracker.get_setting(
        1,
        "graph_theme"
    ) == "dark"



def test_settings_isolated(tracker):

    tracker.create_user(1)
    tracker.create_user(2)


    tracker.set_setting(
        1,
        "graph_theme",
        "dark"
    )


    tracker.set_setting(
        2,
        "graph_theme",
        "light"
    )


    assert tracker.get_setting(
        1,
        "graph_theme"
    ) == "dark"


    assert tracker.get_setting(
        2,
        "graph_theme"
    ) == "light"



# =========================================================
# USER ISOLATION
# =========================================================


def test_records_are_isolated(tracker):

    tracker.create_user(1)
    tracker.create_user(2)


    d=date.today()


    tracker.save_record(
        1,
        d,
        5
    )


    assert tracker.get_record(
        2,
        d
    ) is None