import pytest
from datetime import date

from database import TrackerDatabase


@pytest.fixture
def database(tmp_path):
    db_file = tmp_path / "test.db"
    return TrackerDatabase(str(db_file))

def test_add_or_update_record_creates_record(database):

    database.create_user(1)

    database.add_or_update_record(
        1,
        date(2026, 9, 1),
        5
    )

    result = database.get_record(
        1,
        date(2026, 9, 1)
    )

    assert result == 5

def test_add_or_update_record_updates_existing_record(database):

    database.create_user(1)

    record_date = date(2026, 9, 1)

    database.add_or_update_record(
        1,
        record_date,
        5
    )

    database.add_or_update_record(
        1,
        record_date,
        10
    )

    result = database.get_record(
        1,
        record_date
    )

    assert result == 10


def test_add_or_update_record_isolated_between_users(database):

    database.create_user(1)
    database.create_user(2)

    day = date(2026, 9, 1)

    database.add_or_update_record(
        1,
        day,
        5
    )

    database.add_or_update_record(
        2,
        day,
        20
    )

    assert database.get_record(1, day) == 5
    assert database.get_record(2, day) == 20