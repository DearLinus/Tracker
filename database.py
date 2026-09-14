import sqlite3
from datetime import date


class TrackerDatabase:
    """
    Handles SQLite operations for multi-user Telegram tracker.
    """

    def __init__(self, db_path="tracker.db"):
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)

        self._create_tables()

    def _create_tables(self):
        # Users
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id TEXT PRIMARY KEY,
                username TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Records
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                record_date TEXT NOT NULL,
                count INTEGER NOT NULL CHECK (count >= 0),

                FOREIGN KEY(user_id)
                REFERENCES users(telegram_id),

                UNIQUE(user_id, record_date)
            )
            """
        )

        # Settings
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                user_id TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,

                PRIMARY KEY (user_id, setting_key),

                FOREIGN KEY(user_id)
                REFERENCES users(telegram_id)
            )
            """
        )

        self.connection.commit()


    # =========================================================
    # USERS
    # =========================================================

    def create_user(self, telegram_id, username=None):
        self.connection.execute(
            """
            INSERT OR IGNORE INTO users
            (telegram_id, username)
            VALUES (?, ?)
            """,
            (
                str(telegram_id),
                username
            )
        )

        self.connection.commit()


    # =========================================================
    # RECORDS
    # =========================================================

    def add_or_update_record(
        self,
        user_id,
        record_date,
        count
    ):
        self.connection.execute(
            """
            INSERT INTO records
            (
                user_id,
                record_date,
                count
            )
            VALUES (?, ?, ?)

            ON CONFLICT(user_id, record_date)

            DO UPDATE SET
                count = excluded.count
            """,
            (
                str(user_id),
                record_date.isoformat(),
                count
            )
        )

        self.connection.commit()


    def get_record(
        self,
        user_id,
        record_date
    ):
        cursor = self.connection.execute(
            """
            SELECT count
            FROM records
            WHERE user_id = ?
            AND record_date = ?
            """,
            (
                str(user_id),
                record_date.isoformat()
            )
        )

        row = cursor.fetchone()

        return None if row is None else row[0]


    def get_records(self, user_id):

        cursor = self.connection.execute(
            """
            SELECT record_date, count
            FROM records

            WHERE user_id = ?

            ORDER BY record_date ASC
            """,
            (str(user_id),)
        )

        records = {}

        for record_date, count in cursor.fetchall():
            records[
                date.fromisoformat(record_date)
            ] = count

        return records


    def delete_record(
        self,
        user_id,
        record_date
    ):
        cursor = self.connection.execute(
            """
            DELETE FROM records

            WHERE user_id = ?
            AND record_date = ?
            """,
            (
                str(user_id),
                record_date.isoformat()
            )
        )

        self.connection.commit()

        return cursor.rowcount > 0


    # =========================================================
    # SETTINGS
    # =========================================================

    def get_setting(
        self,
        user_id,
        setting_key
    ):
        cursor = self.connection.execute(
            """
            SELECT setting_value
            FROM settings

            WHERE user_id = ?
            AND setting_key = ?
            """,
            (
                str(user_id),
                setting_key
            )
        )

        row = cursor.fetchone()

        return None if row is None else row[0]


    def set_setting(
        self,
        user_id,
        setting_key,
        setting_value
    ):
        self.connection.execute(
            """
            INSERT INTO settings
            (
                user_id,
                setting_key,
                setting_value
            )
            VALUES (?, ?, ?)

            ON CONFLICT(user_id, setting_key)

            DO UPDATE SET
                setting_value = excluded.setting_value
            """,
            (
                str(user_id),
                setting_key,
                setting_value
            )
        )

        self.connection.commit()


    def close(self):
        self.connection.close()