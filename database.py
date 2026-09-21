import sqlite3
from contextlib import contextmanager
from datetime import date


MIGRATIONS = [
    (
        "001_init_schema",
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            count INTEGER NOT NULL CHECK(count >= 0),
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
            UNIQUE(user_id, record_date)
        );

        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER NOT NULL,
            setting_key TEXT NOT NULL,
            setting_value TEXT NOT NULL,
            PRIMARY KEY(user_id, setting_key),
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        );
        """,
    ),
    (
        "002_add_indexes",
        """
        CREATE INDEX IF NOT EXISTS idx_records_user_date
        ON records(user_id, record_date);

        CREATE INDEX IF NOT EXISTS idx_settings_user_key
        ON settings(user_id, setting_key);
        """,
    ),
    (
        "003_user_states",
        """
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER NOT NULL,
            state_key TEXT NOT NULL,
            state_value TEXT,
            PRIMARY KEY(user_id, state_key),
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        );
        """,
    ),
]


class TrackerDatabase:
    """
    SQLite database layer for multi-user tracker.
    Designed for Telegram bot usage.
    """

    def __init__(self, db_path="tracker.db"):
        self.db_path = db_path
        self._initialize_database()

    # =========================================================
    # CONNECTION
    # =========================================================

    def _get_connection(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @contextmanager
    def connection(self):
        conn = self._get_connection()

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self):
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            self._ensure_schema_migrations_table(connection)
            self._apply_migrations(connection)

    def _ensure_schema_migrations_table(self, connection):
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def get_applied_migrations(self):
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT migration_name FROM schema_migrations ORDER BY migration_name"
            ).fetchall()
            return [row["migration_name"] for row in rows]

    # =========================================================
    # USER STATE (persistence for conversation state)
    # =========================================================

    def set_user_state(self, user_id, state_key, state_value):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO user_states (user_id, state_key, state_value)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, state_key) DO UPDATE SET
                    state_value = excluded.state_value
                """,
                (user_id, state_key, state_value),
            )

    def get_user_state(self, user_id, state_key):
        with self.connection() as connection:
            row = connection.execute(
                "SELECT state_value FROM user_states WHERE user_id = ? AND state_key = ?",
                (user_id, state_key),
            ).fetchone()
            return None if row is None else row["state_value"]

    def delete_user_state(self, user_id, state_key):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM user_states WHERE user_id = ? AND state_key = ?",
                (user_id, state_key),
            )

    def _apply_migrations(self, connection):
        for migration_name, migration_sql in MIGRATIONS:
            existing = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_name = ?",
                (migration_name,),
            ).fetchone()

            if existing is not None:
                continue

            # Start an explicit transaction so that multiple statements
            # within a single migration are applied atomically. If any
            # statement fails, roll back the entire migration.
            connection.execute("BEGIN")

            try:
                # Execute statements one-by-one to avoid implicit executescript
                statements = [s.strip() for s in migration_sql.split(";") if s.strip()]
                for stmt in statements:
                    connection.execute(stmt)

                connection.execute(
                    "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                    (migration_name,),
                )

                # commit the migration transaction
                connection.execute("COMMIT")

            except Exception:
                # Rollback this migration so partial changes are not left behind
                try:
                    connection.execute("ROLLBACK")
                except Exception:
                    # If rollback itself fails, log/raise the original error
                    pass
                raise

    # =========================================================
    # USERS
    # =========================================================

    def create_user(self, telegram_id, username=None):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO users
                (
                    telegram_id,
                    username
                )

                VALUES (?, ?)

                """,
                (
                    telegram_id,
                    username,
                ),
            )

    def user_exists(self, telegram_id):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT 1

                FROM users

                WHERE telegram_id = ?

                LIMIT 1

                """,
                (
                    telegram_id,
                ),
            )
            return cursor.fetchone() is not None

    # =========================================================
    # RECORDS
    # =========================================================

    def add_or_update_record(self, user_id, record_date, count):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO records
                (
                    user_id,
                    record_date,
                    count
                )

                VALUES (?, ?, ?)


                ON CONFLICT(
                    user_id,
                    record_date
                )

                DO UPDATE SET

                    count = excluded.count

                """,
                (
                    user_id,
                    record_date.isoformat(),
                    count,
                ),
            )

    def get_record(self, user_id, record_date):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT count

                FROM records

                WHERE user_id = ?

                AND record_date = ?

                """,
                (
                    user_id,
                    record_date.isoformat(),
                ),
            )

            row = cursor.fetchone()
            return None if row is None else row["count"]

    def get_records(self, user_id):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT
                    record_date,
                    count

                FROM records

                WHERE user_id = ?

                ORDER BY record_date ASC

                """,
                (
                    user_id,
                ),
            )

            records = {}
            for row in cursor.fetchall():
                records[date.fromisoformat(row["record_date"])] = row["count"]

            return records

    def delete_record(self, user_id, record_date):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM records

                WHERE user_id = ?

                AND record_date = ?

                """,
                (
                    user_id,
                    record_date.isoformat(),
                ),
            )

            if cursor.rowcount == 0:
                raise ValueError("Record does not exist.")

            return True

    def delete_user(self, user_id):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM users

                WHERE telegram_id = ?
                """,
                (
                    user_id,
                ),
            )
            return cursor.rowcount > 0

    # =========================================================
    # SETTINGS
    # =========================================================

    def get_setting(self, user_id, setting_key):
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT setting_value

                FROM settings

                WHERE user_id = ?

                AND setting_key = ?

                """,
                (
                    user_id,
                    setting_key,
                ),
            )

            row = cursor.fetchone()
            return None if row is None else row["setting_value"]

    def set_setting(self, user_id, setting_key, setting_value):
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO settings
                (
                    user_id,
                    setting_key,
                    setting_value
                )

                VALUES (?, ?, ?)


                ON CONFLICT(
                    user_id,
                    setting_key
                )

                DO UPDATE SET

                    setting_value =
                    excluded.setting_value

                """,
                (
                    user_id,
                    setting_key,
                    setting_value,
                ),
            )

 