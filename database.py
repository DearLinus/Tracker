import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone

from cryptography.fernet import Fernet, InvalidToken

import config


class RecordDecryptionError(RuntimeError):
    """Raised when database record data cannot be decrypted."""


def _get_fernet() -> Fernet:
    key = getattr(config, "ENCRYPTION_KEY", None)
    if not key:
        raise ValueError("Missing required environment variable: ENCRYPTION_KEY")
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise ValueError("ENCRYPTION_KEY must be a valid Fernet key.") from exc


def _encrypt_count_value(count):
    if not isinstance(count, int):
        raise TypeError("count must be an integer before encryption.")
    token = _get_fernet().encrypt(str(count).encode()).decode()
    return f"enc:{token}"


def _looks_like_encrypted(value):
    if not isinstance(value, str):
        return False
    if not value or not value.startswith("enc:"):
        return False

    # A broken or malformed ENCRYPTION_KEY is a configuration failure, not a
    # legacy-plaintext value. Surface that explicitly so migrations do not keep
    # running in a silently misconfigured state.
    fernet = _get_fernet()
    token = value[4:]

    try:
        fernet.decrypt(token.encode())
    except InvalidToken:
        # Valid encrypted payload, but not decryptable with the active key.
        # This is a legacy/wrong-key case, not a config failure.
        return False
    except (TypeError, ValueError) as exc:
        raise ValueError("Encrypted record value is malformed or corrupted.") from exc

    return True


def _decrypt_count_value(value):
    if value is None:
        raise RecordDecryptionError("Missing encrypted record count.")
    if isinstance(value, int):
        raise RecordDecryptionError("Record count is not encrypted.")
    if not isinstance(value, str):
        raise RecordDecryptionError("Record count format is invalid.")
    if not value.startswith("enc:"):
        raise RecordDecryptionError("Record count is not encrypted.")

    token = value[4:]
    try:
        decrypted = _get_fernet().decrypt(token.encode())
    except (InvalidToken, TypeError, ValueError) as exc:
        raise RecordDecryptionError("Failed to decrypt record count.") from exc

    try:
        return int(decrypted.decode())
    except (TypeError, ValueError) as exc:
        raise RecordDecryptionError("Decrypted record count is invalid.") from exc


def _restore_count_value(value):
    if isinstance(value, str) and value.startswith("enc:"):
        return _decrypt_count_value(value)
    return int(value)


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


def _consolidate_index_cleanup(connection):
    """Consolidate index cleanup: remove duplicates, drop redundant explicit indexes.
    
    This handles three concerns:
    1. Detect and drop indexes that duplicate canonical `idx_records_user_date` and
       `idx_settings_user_key` semantics but have different names.
    2. Drop explicit named indexes when SQLite autoindex (from UNIQUE constraints)
       covers the same columns to avoid redundant indexes.
    3. Ensure the canonical index names are always present unless an autoindex
       already covers them.
    
    Implemented as idempotent Python logic because SQLite SQL cannot easily
    iterate indexes by column list in a single static script.
    """
    canonical = {
        "records": ("idx_records_user_date", ("user_id", "record_date")),
        "settings": ("idx_settings_user_key", ("user_id", "setting_key")),
    }

    for tbl, (canonical_name, canonical_cols) in canonical.items():
        try:
            idx_list = list(connection.execute(f"PRAGMA index_list('{tbl}')"))
        except sqlite3.Error:
            continue

        # Build a map: index_name -> tuple(column names)
        idx_cols = {}
        autoindex_exists = False
        for row in idx_list:
            name = row[1]
            try:
                info = list(connection.execute(f"PRAGMA index_info('{name}')"))
            except sqlite3.Error:
                continue
            cols = tuple(r[2] for r in info)
            idx_cols[name] = cols
            
            # Check if an autoindex already covers the canonical columns
            if name.startswith("sqlite_autoindex_") and cols == tuple(canonical_cols):
                autoindex_exists = True

        # If autoindex exists covering canonical columns, drop the explicit canonical index
        # Otherwise, ensure the explicit canonical index exists
        if autoindex_exists:
            try:
                connection.execute(f'DROP INDEX IF EXISTS "{canonical_name}"')
            except sqlite3.Error:
                pass
        else:
            # Ensure canonical index exists with correct columns if no autoindex covers it
            present_cols = idx_cols.get(canonical_name)
            if present_cols != canonical_cols:
                try:
                    connection.execute(
                        f"CREATE INDEX IF NOT EXISTS {canonical_name} ON {tbl}({', '.join(canonical_cols)})"
                    )
                except sqlite3.Error:
                    pass

        # Drop any other explicit idx_* indexes that duplicate the canonical columns
        # (but do this after we've handled the canonical index itself)
        try:
            idx_list = list(connection.execute(f"PRAGMA index_list('{tbl}')"))
        except sqlite3.Error:
            continue
            
        for row in idx_list:
            name = row[1]
            if name == canonical_name or not name.startswith("idx_"):
                continue
            try:
                info = list(connection.execute(f"PRAGMA index_info('{name}')"))
            except sqlite3.Error:
                continue
            cols = tuple(r[2] for r in info)
            if cols == tuple(canonical_cols):
                try:
                    connection.execute(f'DROP INDEX IF EXISTS "{name}"')
                except sqlite3.Error:
                    # Best-effort: continue cleanup even if a single drop fails
                    pass



# NOTE: 006 was intentionally left unused. Existing databases already include
# the 005 consolidation migration and the later 007 rate-limit migration, so we
# must not renumber 007 or rewrite the historical migration sequence.
MIGRATIONS.append(("005_consolidate_index_cleanup", _consolidate_index_cleanup))


MIGRATIONS.append(
    (
        "007_add_rate_limits",
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            user_id INTEGER NOT NULL,
            operation TEXT NOT NULL,
            window_start TEXT NOT NULL,
            request_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, operation, window_start),
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        );
        """,
    )
)

def _encrypt_record_counts_migration(connection):
    """Encrypt legacy numeric record counts and remove the old INTEGER CHECK schema."""
    try:
        table_info = connection.execute("PRAGMA table_info('records')").fetchall()
    except sqlite3.Error:
        return

    if not table_info:
        return

    count_column = next((col for col in table_info if col[1] == "count"), None)
    if count_column is None:
        return

    existing_rows = connection.execute(
        "SELECT id, user_id, record_date, count FROM records ORDER BY id"
    ).fetchall()

    needs_schema_rebuild = False
    if count_column[2] != "TEXT":
        needs_schema_rebuild = True

    if not needs_schema_rebuild:
        for row in existing_rows:
            raw = row["count"]
            if _looks_like_encrypted(raw):
                continue
            if raw is None:
                continue
            if isinstance(raw, int):
                encrypted = _encrypt_count_value(raw)
            else:
                encrypted = _encrypt_count_value(int(str(raw)))
            connection.execute(
                "UPDATE records SET count = ? WHERE id = ?",
                (encrypted, row["id"]),
            )
        return

    connection.execute("DROP INDEX IF EXISTS idx_records_user_date")
    connection.execute("ALTER TABLE records RENAME TO records_legacy")
    connection.execute(
        """
        CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            count TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
            UNIQUE(user_id, record_date)
        )
        """
    )

    for row in existing_rows:
        raw = row["count"]
        if _looks_like_encrypted(raw):
            encrypted = raw
        elif raw is None:
            encrypted = ""
        else:
            encrypted = _encrypt_count_value(int(raw))

        connection.execute(
            "INSERT INTO records (id, user_id, record_date, count) VALUES (?, ?, ?, ?)",
            (row["id"], row["user_id"], row["record_date"], encrypted),
        )

    connection.execute("DROP TABLE records_legacy")
    # Do not recreate the explicit canonical index here. The UNIQUE(user_id, record_date)
    # constraint already creates the canonical autoindex, and the post-migration cleanup
    # should remove any redundant explicit duplicates rather than reintroducing them.
    _consolidate_index_cleanup(connection)


MIGRATIONS.append(("008_encrypt_record_counts", _encrypt_record_counts_migration))

MIGRATIONS.append(
    (
        "009_pending_deletion",
        """
        CREATE TABLE IF NOT EXISTS user_deletions (
            user_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            deletion_requested_at TEXT NOT NULL,
            deletion_expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_recovery_data (
            user_id INTEGER PRIMARY KEY,
            snapshot TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        );
        """,
    )
)


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
        except sqlite3.Error:
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
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "    migration_name TEXT PRIMARY KEY,"
            "    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ")"
        )

    def get_applied_migrations(self):
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT migration_name FROM schema_migrations"
                " ORDER BY migration_name"
            ).fetchall()
            return [row["migration_name"] for row in rows]

    # =========================================================
    # USER STATE (persistence for conversation state)
    # =========================================================

    def set_user_state(self, user_id, state_key, state_value):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO user_states (user_id, state_key, state_value)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT(user_id, state_key) DO UPDATE SET"
                " state_value = excluded.state_value",
                (user_id, state_key, state_value),
            )

    def get_user_state(self, user_id, state_key):
        with self.connection() as connection:
            row = connection.execute(
                "SELECT state_value FROM user_states"
                " WHERE user_id = ? AND state_key = ?",
                (user_id, state_key),
            ).fetchone()
            return None if row is None else row["state_value"]

    def delete_user_state(self, user_id, state_key):
        with self.connection() as connection:
            connection.execute(
                "DELETE FROM user_states"
                " WHERE user_id = ? AND state_key = ?",
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

            except sqlite3.Error:
                # Rollback this migration so partial changes are not left behind
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    # If rollback itself fails, log/raise the original error
                    pass
                raise

    # =========================================================
    # USERS
    # =========================================================

    def create_user(self, telegram_id, username=None):
        with self.connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username)"
                " VALUES (?, ?)",
                (telegram_id, username),
            )

    def user_exists(self, telegram_id):
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM users WHERE telegram_id = ? LIMIT 1",
                (telegram_id,),
            )
            return cursor.fetchone() is not None

    # =========================================================
    # RECORDS
    # =========================================================

    def add_or_update_record(self, user_id, record_date, count):
        encrypted_count = _encrypt_count_value(count)
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO records (user_id, record_date, count)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT(user_id, record_date)"
                " DO UPDATE SET count = excluded.count",
                (user_id, record_date.isoformat(), encrypted_count),
            )

    def add_or_update_record_require_user(self, user_id, record_date, count):
        """
        Atomically ensure the user exists and insert/update the record
        using a single database connection. This reduces connection churn
        when callers would otherwise check existence then write.
        Raises ValueError if the user does not exist.
        """
        encrypted_count = _encrypt_count_value(count)
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM users WHERE telegram_id = ? LIMIT 1",
                (user_id,),
            )

            if cursor.fetchone() is None:
                raise ValueError("User does not exist.")

            connection.execute(
                "INSERT INTO records (user_id, record_date, count)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT(user_id, record_date)"
                " DO UPDATE SET count = excluded.count",
                (user_id, record_date.isoformat(), encrypted_count),
            )

    def get_record(self, user_id, record_date):
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT count FROM records"
                " WHERE user_id = ? AND record_date = ?",
                (user_id, record_date.isoformat()),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return _decrypt_count_value(row["count"])

    def get_records(self, user_id):
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT record_date, count FROM records"
                " WHERE user_id = ?"
                " ORDER BY record_date ASC",
                (user_id,),
            )
            records = {}
            for row in cursor.fetchall():
                records[date.fromisoformat(row["record_date"])] = _decrypt_count_value(row["count"])
            return records

    def delete_record(self, user_id, record_date):
        with self.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM records"
                " WHERE user_id = ? AND record_date = ?",
                (user_id, record_date.isoformat()),
            )
            if cursor.rowcount == 0:
                raise ValueError("Record does not exist.")
            return True

    def delete_user(self, user_id):
        with self.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM users WHERE telegram_id = ?",
                (user_id,),
            )
            return cursor.rowcount > 0

    def get_pending_deletion(self, user_id):
        with self.connection() as connection:
            row = connection.execute(
                "SELECT user_id, status, deletion_requested_at, deletion_expires_at FROM user_deletions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "user_id": row["user_id"],
                "status": row["status"],
                "deletion_requested_at": row["deletion_requested_at"],
                "deletion_expires_at": row["deletion_expires_at"],
            }

    def set_pending_deletion(self, user_id, deletion_requested_at, deletion_expires_at):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO user_deletions (user_id, status, deletion_requested_at, deletion_expires_at)"
                " VALUES (?, 'pending', ?, ?)"
                " ON CONFLICT(user_id) DO UPDATE SET"
                " status = excluded.status, deletion_requested_at = excluded.deletion_requested_at,"
                " deletion_expires_at = excluded.deletion_expires_at, updated_at = CURRENT_TIMESTAMP",
                (user_id, deletion_requested_at, deletion_expires_at),
            )

    def clear_pending_deletion(self, user_id):
        with self.connection() as connection:
            connection.execute("DELETE FROM user_deletions WHERE user_id = ?", (user_id,))

    def build_recovery_snapshot(self, user_id):
        with self.connection() as connection:
            records = {
                row["record_date"]: _decrypt_count_value(row["count"])
                for row in connection.execute(
                    "SELECT record_date, count FROM records WHERE user_id = ? ORDER BY record_date ASC",
                    (user_id,),
                ).fetchall()
            }
            settings = {
                row["setting_key"]: row["setting_value"]
                for row in connection.execute(
                    "SELECT setting_key, setting_value FROM settings WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
            states = {
                row["state_key"]: row["state_value"]
                for row in connection.execute(
                    "SELECT state_key, state_value FROM user_states WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
            return {"records": records, "settings": settings, "user_states": states}

    def store_user_recovery_data(self, user_id, snapshot):
        with self.connection() as connection:
            payload = json.dumps(snapshot, sort_keys=True)
            connection.execute(
                "INSERT INTO user_recovery_data (user_id, snapshot) VALUES (?, ?)"
                " ON CONFLICT(user_id) DO UPDATE SET snapshot = excluded.snapshot, updated_at = CURRENT_TIMESTAMP",
                (user_id, payload),
            )

    def get_user_recovery_data(self, user_id):
        with self.connection() as connection:
            row = connection.execute(
                "SELECT snapshot FROM user_recovery_data WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row["snapshot"])

    def clear_user_recovery_data(self, user_id):
        with self.connection() as connection:
            connection.execute("DELETE FROM user_recovery_data WHERE user_id = ?", (user_id,))

    def list_due_pending_deletions(self, now):
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT user_id FROM user_deletions WHERE status = 'pending' AND deletion_expires_at <= ?",
                (now.isoformat(),),
            ).fetchall()
            return [row["user_id"] for row in rows]

    def request_pending_deletion_transaction(self, user_id, requested_at, expires_at):
        with self.connection() as connection:
            records = {
                row["record_date"]: _decrypt_count_value(row["count"])
                for row in connection.execute(
                    "SELECT record_date, count FROM records WHERE user_id = ? ORDER BY record_date ASC",
                    (user_id,),
                ).fetchall()
            }
            settings = {
                row["setting_key"]: row["setting_value"]
                for row in connection.execute(
                    "SELECT setting_key, setting_value FROM settings WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
            states = {
                row["state_key"]: row["state_value"]
                for row in connection.execute(
                    "SELECT state_key, state_value FROM user_states WHERE user_id = ?",
                    (user_id,),
                ).fetchall()
            }
            snapshot = {"records": records, "settings": settings, "user_states": states}
            payload = json.dumps(snapshot, sort_keys=True)
            connection.execute(
                "INSERT INTO user_recovery_data (user_id, snapshot) VALUES (?, ?)"
                " ON CONFLICT(user_id) DO UPDATE SET snapshot = excluded.snapshot, updated_at = CURRENT_TIMESTAMP",
                (user_id, payload),
            )
            connection.execute(
                "INSERT INTO user_deletions (user_id, status, deletion_requested_at, deletion_expires_at)"
                " VALUES (?, 'pending', ?, ?)"
                " ON CONFLICT(user_id) DO UPDATE SET"
                " status = excluded.status, deletion_requested_at = excluded.deletion_requested_at,"
                " deletion_expires_at = excluded.deletion_expires_at, updated_at = CURRENT_TIMESTAMP",
                (user_id, requested_at, expires_at),
            )
            return {"status": "pending", "requested_at": requested_at, "expires_at": expires_at}

    def restore_pending_deletion_transaction(self, user_id, now_value):
        with self.connection() as connection:
            row = connection.execute(
                "SELECT deletion_expires_at FROM user_deletions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return False

            expires_at = datetime.fromisoformat(row["deletion_expires_at"])
            if now_value >= expires_at:
                return False

            recovery_row = connection.execute(
                "SELECT snapshot FROM user_recovery_data WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if recovery_row is not None:
                snapshot = json.loads(recovery_row["snapshot"])
                if "records" in snapshot:
                    connection.execute("DELETE FROM records WHERE user_id = ?", (user_id,))
                    for record_date_text, count in snapshot["records"].items():
                        connection.execute(
                            "INSERT INTO records (user_id, record_date, count) VALUES (?, ?, ?)",
                            (user_id, record_date_text, _encrypt_count_value(_restore_count_value(count))),
                        )
                if "settings" in snapshot:
                    connection.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
                    for key, value in snapshot["settings"].items():
                        connection.execute(
                            "INSERT INTO settings (user_id, setting_key, setting_value) VALUES (?, ?, ?)",
                            (user_id, key, value),
                        )
                if "user_states" in snapshot:
                    connection.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
                    for key, value in snapshot["user_states"].items():
                        connection.execute(
                            "INSERT INTO user_states (user_id, state_key, state_value) VALUES (?, ?, ?)",
                            (user_id, key, value),
                        )

            connection.execute("DELETE FROM user_deletions WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM user_recovery_data WHERE user_id = ?", (user_id,))
            return True

    def purge_user_data(self, user_id):
        with self.connection() as connection:
            connection.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM records WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM user_recovery_data WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM user_deletions WHERE user_id = ?", (user_id,))
            connection.execute("DELETE FROM users WHERE telegram_id = ?", (user_id,))

    def restore_user_snapshot(self, user_id, snapshot):
        if not snapshot:
            return
        with self.connection() as connection:
            if "records" in snapshot:
                connection.execute("DELETE FROM records WHERE user_id = ?", (user_id,))
                for record_date_text, count in snapshot["records"].items():
                    connection.execute(
                        "INSERT INTO records (user_id, record_date, count) VALUES (?, ?, ?)",
                        (user_id, record_date_text, _encrypt_count_value(_restore_count_value(count))),
                    )
            if "settings" in snapshot:
                connection.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
                for key, value in snapshot["settings"].items():
                    connection.execute(
                        "INSERT INTO settings (user_id, setting_key, setting_value) VALUES (?, ?, ?)",
                        (user_id, key, value),
                    )
            if "user_states" in snapshot:
                connection.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
                for key, value in snapshot["user_states"].items():
                    connection.execute(
                        "INSERT INTO user_states (user_id, state_key, state_value) VALUES (?, ?, ?)",
                        (user_id, key, value),
                    )

    # =========================================================
    # SETTINGS
    # =========================================================

    def get_all_settings(self, user_id):
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT setting_key, setting_value FROM settings WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            return {row["setting_key"]: row["setting_value"] for row in rows}

    def get_all_user_states(self, user_id):
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT state_key, state_value FROM user_states WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            return {row["state_key"]: row["state_value"] for row in rows}

    def get_setting(self, user_id, setting_key):
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT setting_value FROM settings"
                " WHERE user_id = ? AND setting_key = ?",
                (user_id, setting_key),
            )
            row = cursor.fetchone()
            return None if row is None else row["setting_value"]

    def set_setting(self, user_id, setting_key, setting_value):
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO settings (user_id, setting_key, setting_value)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT(user_id, setting_key)"
                " DO UPDATE SET setting_value = excluded.setting_value",
                (user_id, setting_key, setting_value),
            )

    # =========================================================
    # RATE LIMITS
    # =========================================================

    def check_and_record_rate_limit(self, user_id, operation, limit, window_seconds, now=None):
        """Allow up to `limit` requests in each fixed time window for a user/operation.

        Bucket membership is keyed by the number of full window intervals elapsed since the
        Unix epoch. This ensures all requests within the same fixed window share the same
        bucket regardless of when inside the window they occur, while older buckets are
        naturally discarded as new window boundaries are crossed.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        epoch_seconds = int(now.timestamp())
        bucket_epoch = (epoch_seconds // window_seconds) * window_seconds
        bucket_start = datetime.fromtimestamp(bucket_epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self.connection() as connection:
            connection.execute(
                "DELETE FROM rate_limits WHERE user_id = ? AND operation = ? AND window_start < ?",
                (user_id, operation, bucket_start),
            )

            row = connection.execute(
                "SELECT request_count FROM rate_limits WHERE user_id = ? AND operation = ? AND window_start = ?",
                (user_id, operation, bucket_start),
            ).fetchone()

            current_count = 0 if row is None else int(row["request_count"])

            if current_count >= limit:
                return False

            updated_count = current_count + 1
            connection.execute(
                """
                INSERT INTO rate_limits (user_id, operation, window_start, request_count, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, operation, window_start)
                DO UPDATE SET request_count = excluded.request_count, updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, operation, bucket_start, updated_count),
            )
            return True

 