import os
import sqlite3
from backup import backup_database


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

    try:
        backup_database(str(db), str(backup_dir))
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


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

    path = backup_database(str(db), str(backup_dir))
    # after backup, only the 2 newest timestamped backups should remain
    import re
    pattern = re.compile(rf"^{stem}_\d{{8}}_\d{{6}}.*\.db$")
    timestamped = [p for p in backup_dir.iterdir() if p.is_file() and pattern.match(p.name)]
    assert len(timestamped) <= 2
