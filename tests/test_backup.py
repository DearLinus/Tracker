import os
import sqlite3

import pytest

from backup import backup_database, restore_database


def test_backup_captures_wal_state(tmp_path):
    db_path = tmp_path / "wal.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO items (value) VALUES ('wal-row')")
        conn.commit()
    finally:
        conn.close()

    backup_dir = tmp_path / "backups"
    backup_path = backup_database(str(db_path), str(backup_dir))

    with sqlite3.connect(backup_path) as backup_conn:
        row = backup_conn.execute("SELECT value FROM items WHERE value = 'wal-row'").fetchone()
        assert row is not None
        assert row[0] == "wal-row"


def test_backup_success(tmp_path):
    db = tmp_path / "test.db"
    # create a simple DB
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE foo (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_path = backup_database(str(db), str(backup_dir))

    assert os.path.exists(backup_path)


def test_backup_missing_source_raises(tmp_path):
    db = tmp_path / "does_not_exist.db"
    backup_dir = tmp_path / "backups"

    with pytest.raises(FileNotFoundError):
        backup_database(str(db), str(backup_dir))


def test_backup_retention(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE foo (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    os.makedirs(backup_dir, exist_ok=True)

    # create several fake timestamped backup files that match our naming convention
    stem = db.stem
    timestamps = [f"2026010{i}_00000{i}" for i in range(5)]
    for ts in timestamps:
        p = backup_dir / f"{stem}_{ts}.db"
        p.write_text("x")

    # set retention to 2
    monkeypatch.setenv("BACKUP_RETENTION", "2")

    backup_database(str(db), str(backup_dir))
    # after backup, only the 2 newest timestamped backups should remain
    import re
    pattern = re.compile(rf"^{stem}_\d{{8}}_\d{{6}}.*\.db$")
    timestamped = [p for p in backup_dir.iterdir() if p.is_file() and pattern.match(p.name)]
    assert len(timestamped) <= 2


def make_simple_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT);")
    cur.execute("INSERT INTO t (x) VALUES ('a')")
    conn.commit()
    conn.close()


def test_backup_and_restore_roundtrip(tmp_path):
    db = tmp_path / "test.db"
    make_simple_db(db)

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    backup_path = backup_database(str(db), str(backup_dir))
    assert os.path.exists(backup_path)

    # restore to a new path
    restored = tmp_path / "restored.db"
    restore_database(str(restored), backup_path)

    # restored DB should contain the table
    conn = sqlite3.connect(restored)
    cur = conn.cursor()
    cur.execute("SELECT x FROM t")
    rows = cur.fetchall()
    conn.close()
    assert rows == [("a",)]


def test_restore_fails_on_nonexistent_backup(tmp_path):
    target = tmp_path / "target.db"
    with pytest.raises(FileNotFoundError):
        restore_database(str(target), str(tmp_path / "nope.db"))


def test_restore_fails_on_corrupted_backup(tmp_path):
    # create a non-sqlite file
    bad = tmp_path / "bad.db"
    bad.write_text("not a sqlite")

    target = tmp_path / "target.db"

    with pytest.raises(ValueError):
        restore_database(str(target), str(bad))


def test_restore_creates_safety_copy(tmp_path):
    db = tmp_path / "test.db"
    make_simple_db(db)

    # create a second value so we can see difference post-restore
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO t (x) VALUES ('b')")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    backup_path = backup_database(str(db), str(backup_dir))

    # mutate original to simulate mid-restore change
    conn = sqlite3.connect(db)
    conn.execute("DELETE FROM t WHERE x='b'")
    conn.commit()
    conn.close()

    # restore should create a safety copy of current DB before overwrite
    restore_database(str(db), backup_path)

    # find pre_restore file
    pre = list(tmp_path.glob("test.db.pre_restore_*.db"))
    assert pre, "safety pre-restore file not created"

    # safety copy should contain the truncated state (without 'b')
    conn = sqlite3.connect(pre[0])
    rows = conn.execute("SELECT x FROM t ORDER BY id").fetchall()
    conn.close()
    assert ("a",) in rows
