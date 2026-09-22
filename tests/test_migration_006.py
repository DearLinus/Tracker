import os
import sqlite3
import tempfile

from database import TrackerDatabase


def test_migration_006_drops_explicit_idx(tmp_path):
    fd, path = tempfile.mkstemp(suffix='.db', dir=str(tmp_path))
    os.close(fd)

    # Initialize DB which will run migrations including 005 (consolidated cleanup)
    TrackerDatabase(path)

    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row

    rec_indexes = list(con.execute("PRAGMA index_list('records')"))
    names = [r[1] for r in rec_indexes]

    # After consolidation, the explicit index should be dropped because
    # the UNIQUE(user_id, record_date) constraint creates sqlite_autoindex_records_*
    # which covers the same columns. The explicit index is now redundant.
    assert not any(n == 'idx_records_user_date' for n in names)
    assert any(n.startswith('sqlite_autoindex_records_') for n in names)
    assert not any(n.endswith('_dup') for n in names)

    set_indexes = list(con.execute("PRAGMA index_list('settings')"))
    snames = [r[1] for r in set_indexes]

    # Similarly for settings: the explicit index should be dropped because
    # PRIMARY KEY(user_id, setting_key) creates sqlite_autoindex_settings_*
    assert not any(n == 'idx_settings_user_key' for n in snames)
    assert any(n.startswith('sqlite_autoindex_settings_') for n in snames)
    assert not any(n.endswith('_dup') for n in snames)

    con.close()
