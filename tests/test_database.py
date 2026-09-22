import sqlite3
import sys
from datetime import date

import pytest

from backup import backup_database, restore_database
from backup import main as backup_main
from database import TrackerDatabase


@pytest.fixture
def database(tmp_path):
    db_file = tmp_path / "test.db"
    return TrackerDatabase(str(db_file))


def test_database_tracks_applied_migrations(database):
    migrations = database.get_applied_migrations()

    assert "001_init_schema" in migrations
    assert "002_add_indexes" in migrations


def test_migration_list_is_in_numeric_order():
    import database as db_module

    migration_names = [name for name, _ in db_module.MIGRATIONS]
    numeric_prefixes = [int(name.split("_", 1)[0]) for name in migration_names]

    assert numeric_prefixes == sorted(numeric_prefixes), (
        "MIGRATIONS must be ordered numerically by migration prefix: "
        f"{migration_names}"
    )


def test_apply_migrations_rolls_back_failed_migration(tmp_path, monkeypatch):
    db = TrackerDatabase(str(tmp_path / "rollback.db"))

    module = sys.modules["database"]
    monkeypatch.setattr(
        module,
        "MIGRATIONS",
        [("bad_migration", "CREATE TABLE broken (id INTEGER")],
    )

    with pytest.raises(sqlite3.Error), db.connection() as connection:
        db._apply_migrations(connection)

    applied = db.get_applied_migrations()
    assert "bad_migration" not in applied


def test_backup_database_creates_backup(tmp_path):
    source = tmp_path / "tracker.db"
    backup_dir = tmp_path / "backups"

    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test (id) VALUES (1)")

    backup_path = backup_database(str(source), str(backup_dir))

    assert backup_path.endswith(".db")
    assert backup_dir.exists()
    # Expect at least one timestamped backup file for this source DB
    assert any(p.is_file() for p in backup_dir.iterdir())

    with sqlite3.connect(backup_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM test").fetchone()
    assert row[0] == 1


def test_delete_user_removes_user_and_related_data(database):
    database.create_user(10, "tester")
    database.set_setting(10, "graph_theme", "dark")
    database.add_or_update_record(10, date(2026, 9, 1), 5)

    database.delete_user(10)

    assert database.user_exists(10) is False
    assert database.get_setting(10, "graph_theme") is None
    assert database.get_record(10, date(2026, 9, 1)) is None


def test_backup_cli_creates_backup(tmp_path, monkeypatch):
    source = tmp_path / "data" / "tracker.db"
    backup_dir = tmp_path / "backups"
    source.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test (id) VALUES (1)")

    monkeypatch.setattr(
        sys,
        "argv",
        ["backup.py", "backup", "--db-path", str(source), "--backup-dir", str(backup_dir)],
    )

    backup_main()

    assert backup_dir.exists()
    assert any(backup_dir.iterdir())


def test_backup_cli_restores_backup(tmp_path, monkeypatch):
    source = tmp_path / "data" / "tracker.db"
    backup_dir = tmp_path / "backups"
    source.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES ('before')")

    backup_path = backup_database(str(source), str(backup_dir))

    with sqlite3.connect(source) as conn:
        conn.execute("DELETE FROM test")
        conn.execute("INSERT INTO test (value) VALUES ('after')")

    monkeypatch.setattr(
        sys,
        "argv",
        ["backup.py", "restore", "--db-path", str(source), "--backup-file", str(backup_path)],
    )

    backup_main()

    with sqlite3.connect(source) as conn:
        values = conn.execute("SELECT value FROM test").fetchall()

    assert values == [("before",)]


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


def test_callable_migration_rollback_cleans_up_partial_changes(tmp_path, monkeypatch):
    db = TrackerDatabase(str(tmp_path / "callable_rollback.db"))

    def failing_migration(connection):
        connection.execute("CREATE TABLE should_not_exist (id INTEGER)")
        raise sqlite3.Error("boom")

    monkeypatch.setattr(
        sys.modules["database"],
        "MIGRATIONS",
        [("bad_callable_migration", failing_migration)],
    )

    with pytest.raises(sqlite3.Error, match="boom"), db.connection() as connection:
        db._apply_migrations(connection)

    applied = db.get_applied_migrations()
    assert "bad_callable_migration" not in applied

    with sqlite3.connect(str(tmp_path / "callable_rollback.db")) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='should_not_exist'"
        ).fetchall()

    assert tables == []


def test_remove_duplicate_indexes_drops_noncanonical_duplicates(tmp_path):
    db_path = tmp_path / "duplicate_indexes.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE records (user_id INTEGER, record_date TEXT, value INTEGER)"
        )
        conn.execute(
            "CREATE TABLE settings (user_id INTEGER, setting_key TEXT, value TEXT)"
        )
        conn.execute(
            "CREATE INDEX idx_records_user_date_dup ON records(user_id, record_date)"
        )
        conn.execute(
            "CREATE INDEX idx_settings_user_key_dup ON settings(user_id, setting_key)"
        )
        conn.execute(
            "CREATE INDEX idx_records_user_date ON records(user_id, record_date)"
        )
        conn.execute(
            "CREATE INDEX idx_settings_user_key ON settings(user_id, setting_key)"
        )

        from database import _consolidate_index_cleanup

        _consolidate_index_cleanup(conn)

        duplicate_records = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='records' AND name LIKE 'idx_%'"
        ).fetchall()
        duplicate_settings = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='settings' AND name LIKE 'idx_%'"
        ).fetchall()

    assert ("idx_records_user_date",) in duplicate_records
    assert ("idx_settings_user_key",) in duplicate_settings
    assert ("idx_records_user_date_dup",) not in duplicate_records
    assert ("idx_settings_user_key_dup",) not in duplicate_settings