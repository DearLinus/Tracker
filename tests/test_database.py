import pytest
import shutil
from datetime import date

from database import TrackerDatabase
from backup import backup_database


@pytest.fixture
def database(tmp_path):
    db_file = tmp_path / "test.db"
    return TrackerDatabase(str(db_file))


def test_database_tracks_applied_migrations(database):
    migrations = database.get_applied_migrations()

    assert "001_init_schema" in migrations
    assert "002_add_indexes" in migrations

def test_backup_database_creates_backup(tmp_path):
    source = tmp_path / "tracker.db"
    backup_dir = tmp_path / "backups"
    source.write_text("dummy database")

    backup_path = backup_database(str(source), str(backup_dir))

    assert backup_path.endswith(".db")
    assert backup_dir.exists()
    assert backup_dir.joinpath(source.name).exists()

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