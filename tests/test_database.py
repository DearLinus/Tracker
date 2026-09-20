import sqlite3

import pytest
from datetime import date

from database import TrackerDatabase
from backup import backup_database, restore_database


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

    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test (id) VALUES (1)")

    backup_path = backup_database(str(source), str(backup_dir))

    assert backup_path.endswith(".db")
    assert backup_dir.exists()
    assert backup_dir.joinpath(source.name).exists()

    with sqlite3.connect(backup_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM test").fetchone()
    assert row[0] == 1


def test_create_user_is_idempotent(database):
    database.create_user(10, "tester")
    database.create_user(10, "tester")

    with database.connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM users WHERE telegram_id = 10"
        ).fetchone()

    assert row["total"] == 1


def test_set_setting_updates_existing_value(database):
    database.create_user(20)
    database.set_setting(20, "graph_theme", "dark")
    database.set_setting(20, "graph_theme", "light")

    assert database.get_setting(20, "graph_theme") == "light"


def test_restore_database_restores_backup(tmp_path):
    source = tmp_path / "tracker.db"
    backup_dir = tmp_path / "backups"

    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES ('before')")

    backup_path = backup_database(str(source), str(backup_dir))

    with sqlite3.connect(source) as conn:
        conn.execute("DELETE FROM test")
        conn.execute("INSERT INTO test (value) VALUES ('after')")

    restore_database(str(source), backup_path)

    with sqlite3.connect(source) as conn:
        values = conn.execute("SELECT value FROM test").fetchall()

    assert values == [("before",)]

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