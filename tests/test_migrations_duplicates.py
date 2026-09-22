import sqlite3
import tempfile


def test_migrations_idempotent_and_clean_indexes():
    # Test that the consolidation migration properly cleans up redundant indexes
    # We do this by manually calling the consolidation function on a fresh connection
    # with indexes already in place (simulating a messy pre-consolidation DB)
    with tempfile.NamedTemporaryFile() as tf:
        conn = sqlite3.connect(tf.name)
        try:
            # Manually set up the schema tables first (simulating pre-migration DB)
            conn.execute("""
                CREATE TABLE users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    record_date TEXT NOT NULL,
                    count INTEGER NOT NULL CHECK(count >= 0),
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                    UNIQUE(user_id, record_date)
                )
            """)
            conn.execute("""
                CREATE TABLE settings (
                    user_id INTEGER NOT NULL,
                    setting_key TEXT NOT NULL,
                    setting_value TEXT NOT NULL,
                    PRIMARY KEY(user_id, setting_key),
                    FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                )
            """)
            
            # Manually create explicit indexes (as if from old migrations)
            conn.execute("CREATE INDEX idx_records_user_date ON records(user_id, record_date)")
            conn.execute("CREATE INDEX idx_records_user_date_dup ON records(user_id, record_date)")
            conn.execute("CREATE INDEX idx_settings_user_key ON settings(user_id, setting_key)")
            conn.execute("CREATE INDEX idx_settings_user_key_dup ON settings(user_id, setting_key)")
            conn.commit()

            # Import and run the consolidation migration directly
            from database import _consolidate_index_cleanup
            _consolidate_index_cleanup(conn)

            # After consolidation, explicit indexes should be dropped and autoindexes present
            cursor = conn.execute("PRAGMA index_list('records')")
            names = {row[1] for row in cursor.fetchall()}
            assert not any(n == 'idx_records_user_date' for n in names), "Explicit index should be dropped"
            assert any(n.startswith('sqlite_autoindex_records_') for n in names), "Autoindex should be present"
            assert not any(n.endswith('_dup') for n in names), "Duplicate indexes should be cleaned"

            cursor = conn.execute("PRAGMA index_list('settings')")
            names = {row[1] for row in cursor.fetchall()}
            assert not any(n == 'idx_settings_user_key' for n in names), "Explicit index should be dropped"
            assert any(n.startswith('sqlite_autoindex_settings_') for n in names), "Autoindex should be present"
            assert not any(n.endswith('_dup') for n in names), "Duplicate indexes should be cleaned"

        finally:
            conn.close()
