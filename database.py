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
    (
        "004_clean_indexes",
        """
        -- Ensure expected indexes exist and remove duplicates if present.
        -- This uses DROP INDEX IF EXISTS which is safe on SQLite and
        -- is idempotent for already-clean databases.
        DROP INDEX IF EXISTS idx_records_user_date;
        DROP INDEX IF EXISTS idx_settings_user_key;

        CREATE INDEX IF NOT EXISTS idx_records_user_date
        ON records(user_id, record_date);

        CREATE INDEX IF NOT EXISTS idx_settings_user_key
        ON settings(user_id, setting_key);
        """,
    ),
]


def _remove_duplicate_indexes(connection):
    """
    Detect indexes that duplicate the canonical `idx_records_user_date`
    and `idx_settings_user_key` semantics but have different names,
    and drop them. This is implemented in Python because SQLite SQL
    itself does not provide a simple way to iterate and DROP indexes
    by their column list in a single static script.
    """
    canonical = {
        "records": ("idx_records_user_date", ("user_id", "record_date")),
        "settings": ("idx_settings_user_key", ("user_id", "setting_key")),
    }

    for tbl, (canonical_name, cols) in canonical.items():
        cursor = connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name = ?",
            (tbl,),
        )

        for row in cursor.fetchall():
            name = row[0]
            sql = row[1]
            if sql is None:
                # implicit indexes (e.g. for PKs) may have NULL sql; ignore
                continue

            low = sql.lower()
            if all(c.lower() in low for c in cols) and name != canonical_name:
                try:
                    connection.execute(f'DROP INDEX IF EXISTS "{name}"')
                except Exception:
                    # best-effort: don't stop the whole migration on a single drop failure
                    pass


# Append a Python-backed migration that will run once and clean up any
# duplicate indexes discovered at runtime. This keeps previous migrations
# unchanged while providing an idempotent cleanup step.
MIGRATIONS.append(("005_remove_duplicate_indexes", _remove_duplicate_indexes))


def _drop_explicit_redundant_indexes(connection):
    """
    Drop explicit, named indexes (like `idx_records_user_date`) when SQLite
    already created an implicit index (sqlite_autoindex_*) covering the same
    columns (typically for PRIMARY KEY or UNIQUE constraints). This avoids
    redundant indexes that waste space and slow writes.
    """
    canonical = {
        "records": ("idx_records_user_date", ("user_id", "record_date")),
        "settings": ("idx_settings_user_key", ("user_id", "setting_key")),
    }

    for tbl, (canonical_name, canonical_cols) in canonical.items():
        try:
            idx_list = list(connection.execute(f"PRAGMA index_list('{tbl}')"))
        except Exception:
            continue

        # Build a map: index_name -> tuple(column names)
        idx_cols = {}
        for row in idx_list:
            name = row[1]
            try:
                info = list(connection.execute(f"PRAGMA index_info('{name}')"))
            except Exception:
                continue
            cols = tuple(r[2] for r in info)
            idx_cols[name] = cols

        # If canonical index is missing or has different columns, create it
        present_cols = idx_cols.get(canonical_name)
        if present_cols != canonical_cols:
            try:
                # create canonical index if not present (idempotent)
                connection.execute(
                    f"CREATE INDEX IF NOT EXISTS {canonical_name} ON {tbl}({', '.join(canonical_cols)})"
                )
                # refresh idx_cols
                idx_list = list(connection.execute(f"PRAGMA index_list('{tbl}')"))
                idx_cols = {}
                for row in idx_list:
                    name = row[1]
                    try:
                        info = list(connection.execute(f"PRAGMA index_info('{name}')"))
                    except Exception:
                        continue
                    cols = tuple(r[2] for r in info)
                    idx_cols[name] = cols
            except Exception:
                pass

        # Now drop any explicit idx_* that duplicate the canonical columns but are not the canonical name
        for name, cols in list(idx_cols.items()):
            if name == canonical_name:
                continue
            if name.startswith("idx_") and cols == tuple(canonical_cols):
                try:
                    connection.execute(f'DROP INDEX IF EXISTS "{name}"')
                except Exception:
                    pass


# New migration 006: drop explicit indexes redundant with sqlite_autoindex
MIGRATIONS.append(("006_drop_explicit_indexes_redundant_with_autoindex", _drop_explicit_redundant_indexes))


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
                # Support two migration types:
                # - SQL text (string): split into statements and execute
                # - Python callable: call it with the active connection
                if callable(migration_sql):
                    # Callable migrations receive the active connection
                    migration_sql(connection)
                else:
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

    def add_or_update_record_require_user(self, user_id, record_date, count):
        """
        Atomically ensure the user exists and insert/update the record
        using a single database connection. This reduces connection churn
        when callers would otherwise check existence then write.
        Raises ValueError if the user does not exist.
        """
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM users WHERE telegram_id = ? LIMIT 1",
                (user_id,),
            )

            if cursor.fetchone() is None:
                raise ValueError("User does not exist.")

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

 