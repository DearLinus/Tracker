import sqlite3
from datetime import date


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
            timeout=30
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection


    def _initialize_database(self):
        with self._get_connection() as connection:

            connection.execute(
                "PRAGMA journal_mode=WAL"
            )

            self._create_tables(connection)
            self._create_indexes(connection)


    # =========================================================
    # TABLES
    # =========================================================

    def _create_tables(self, connection):

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id TEXT PRIMARY KEY,
                username TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id TEXT NOT NULL,
                record_date TEXT NOT NULL,
                count INTEGER NOT NULL CHECK(count >= 0),

                FOREIGN KEY(user_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE,

                UNIQUE(user_id, record_date)
            )
            """
        )


        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (

                user_id TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,

                PRIMARY KEY(
                    user_id,
                    setting_key
                ),

                FOREIGN KEY(user_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE
            )
            """
        )


    def _create_indexes(self, connection):

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_records_user
            ON records(user_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_records_date
            ON records(record_date)
            """
        )


    # =========================================================
    # USERS
    # =========================================================

    def create_user(
        self,
        telegram_id,
        username=None
    ):

        with self._get_connection() as connection:

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
                    str(telegram_id),
                    username
                )
            )


    # =========================================================
    # RECORDS
    # =========================================================

    def add_or_update_record(
        self,
        user_id,
        record_date,
        count
    ):

        with self._get_connection() as connection:

            connection.execute(
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


    def get_record(
        self,
        user_id,
        record_date
    ):

        with self._get_connection() as connection:

            cursor = connection.execute(
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


    def get_records(
        self,
        user_id
    ):

        with self._get_connection() as connection:

            cursor = connection.execute(
                """
                SELECT record_date, count

                FROM records

                WHERE user_id = ?

                ORDER BY record_date ASC
                """,
                (
                    str(user_id),
                )
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

        with self._get_connection() as connection:

            cursor = connection.execute(
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

            return cursor.rowcount > 0


    # =========================================================
    # SETTINGS
    # =========================================================

    def get_setting(
        self,
        user_id,
        setting_key
    ):

        with self._get_connection() as connection:

            cursor = connection.execute(
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

        with self._get_connection() as connection:

            connection.execute(
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

                    setting_value =
                    excluded.setting_value
                """,
                (
                    str(user_id),
                    setting_key,
                    setting_value
                )
            )


    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):
        pass