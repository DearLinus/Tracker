import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from backup import backup_database, restore_database


def create_simple_db(path):
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE foo (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO foo (val) VALUES ('a'), ('b')")
        conn.commit()
    finally:
        conn.close()


def test_backup_file_missing_source_raises(tmp_path):
    db = tmp_path / "nope.db"
    outdir = tmp_path / "backups"
    with pytest.raises(FileNotFoundError):
        backup_database(str(db), str(outdir))


def test_backup_creates_file_and_respects_retention(tmp_path, monkeypatch):
    fd, path = tempfile.mkstemp(dir=str(tmp_path), suffix='.db')
    os.close(fd)
    create_simple_db(path)
    outdir = tmp_path / "backups"
    monkeypatch.setenv("BACKUP_RETENTION", "1")

    b1 = backup_database(path, str(outdir))
    assert os.path.exists(b1)

    # create another backup; with retention=1 the older backup should be pruned
    backup_database(path, str(outdir))
    files = list(Path(outdir).iterdir())
    assert len(files) == 1


def test_restore_missing_backup_raises(tmp_path):
    db = tmp_path / "target.db"
    backup = tmp_path / "nope.db"

    with pytest.raises(FileNotFoundError):
        restore_database(str(db), str(backup))


def test_restore_with_invalid_backup_raises(tmp_path):
    # create a file that's not a sqlite db
    bad = tmp_path / "bad.db"
    bad.write_text("not sqlite")
    target = tmp_path / "target.db"

    with pytest.raises(ValueError):
        restore_database(str(target), str(bad))


def test_restore_overwrites_and_creates_safety_copy(tmp_path):
    # create a real DB to restore into
    target = tmp_path / "target.db"
    create_simple_db(str(target))

    # make a backup
    fd, bpath = tempfile.mkstemp(dir=str(tmp_path), suffix='.db')
    os.close(fd)
    create_simple_db(bpath)

    # modify target to ensure safety copy is different
    conn = sqlite3.connect(str(target))
    conn.execute("INSERT INTO foo (val) VALUES ('c')")
    conn.commit()
    conn.close()

    restore_database(str(target), str(bpath))

    # safety copy should exist with .pre_restore_ in name
    copies = list(Path('.').glob('*.pre_restore_*.db'))
    # search in tmp_path specifically
    copies = list(Path(tmp_path).glob('target.db.pre_restore_*.db'))
    assert len(copies) == 1


def test_multiple_restores_in_a_row(tmp_path):
    # ensure multiple restores succeed
    target = tmp_path / "target2.db"
    create_simple_db(str(target))

    fd, b1 = tempfile.mkstemp(dir=str(tmp_path), suffix='.db')
    os.close(fd)
    create_simple_db(b1)

    fd, b2 = tempfile.mkstemp(dir=str(tmp_path), suffix='.db')
    os.close(fd)
    create_simple_db(b2)

    restore_database(str(target), str(b1))
    restore_database(str(target), str(b2))

    # final DB should be valid sqlite
    conn = sqlite3.connect(str(target))
    cur = conn.execute("SELECT COUNT(*) FROM foo")
    assert cur.fetchone()[0] == 2
    conn.close()


def test_restore_safety_copies_respect_retention(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_RETENTION", "1")
    target = tmp_path / "target.db"
    create_simple_db(str(target))

    backup = tmp_path / "backup.db"
    create_simple_db(str(backup))

    for ts in ["20250101_010101", "20250102_020202"]:
        safety = tmp_path / f"target.db.pre_restore_{ts}.db"
        create_simple_db(str(safety))

    restore_database(str(target), str(backup))

    safety_copies = sorted(tmp_path.glob("target.db.pre_restore_*.db"))
    assert len(safety_copies) == 1
    assert safety_copies[0].name.endswith(".db")
