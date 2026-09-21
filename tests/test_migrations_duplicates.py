import sqlite3
import tempfile
from database import TrackerDatabase, MIGRATIONS


def test_migrations_idempotent_and_clean_indexes():
    # Create a temp database and apply migrations twice to simulate duplicates
    with tempfile.NamedTemporaryFile() as tf:
        db = TrackerDatabase(db_path=tf.name)

        # Manually create duplicate indexes to simulate a messy DB
        conn = sqlite3.connect(tf.name)
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_user_date ON records(user_id, record_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_user_date_dup ON records(user_id, record_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_settings_user_key_dup ON settings(user_id, setting_key)")
            conn.commit()

            # Re-run migrations (simulate upgrade) which include cleanup
            db._apply_migrations(conn)

            # After migrations, only the canonical indexes should exist (by name)
            cursor = conn.execute("PRAGMA index_list('records')")
            names = {row[1] for row in cursor.fetchall()}
            assert 'idx_records_user_date' in names

            cursor = conn.execute("PRAGMA index_list('settings')")
            names = {row[1] for row in cursor.fetchall()}
            assert 'idx_settings_user_key' in names

        finally:
            conn.close()
