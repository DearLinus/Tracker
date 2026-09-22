import os
import sqlite3
import tempfile

from database import TrackerDatabase


def test_migration_006_drops_explicit_idx(tmp_path):
    fd, path = tempfile.mkstemp(suffix='.db', dir=str(tmp_path))
    os.close(fd)

    # Initialize DB which will run migrations including 006
    TrackerDatabase(path)

    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row

    rec_indexes = list(con.execute("PRAGMA index_list('records')"))
    names = [r[1] for r in rec_indexes]

    # The UNIQUE(user_id, record_date) constraint creates the canonical autoindex.
    # The redundant explicit index should be cleaned up during migration.
    assert not any(n == 'idx_records_user_date' for n in names)
    assert any(n.startswith('sqlite_autoindex_records_') for n in names)
    assert not any(n.endswith('_dup') for n in names)

    set_indexes = list(con.execute("PRAGMA index_list('settings')"))
    snames = [r[1] for r in set_indexes]

    assert any(n == 'idx_settings_user_key' for n in snames)
    assert not any(n.endswith('_dup') for n in snames)

    con.close()
