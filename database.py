import sqlite3
from datetime import date
from contextlib import contextmanager


class TrackerDatabase:
    """
    SQLite database layer for multi-user tracker.
    Designed for Telegram bot usage.
    """


    def __init__(
        self,
        db_path="tracker.db"
    ):
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

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        return connection



    @contextmanager
    def connection(self):

        conn = self._get_connection()

        try:
            yield conn

        finally:
            conn.close()



    def _initialize_database(self):

        with self.connection() as connection:

            connection.execute(
                "PRAGMA journal_mode=WAL"
            )

            self._create_tables(
                connection
            )



    # =========================================================
    # TABLES
    # =========================================================


    def _create_tables(
        self,
        connection
    ):


        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                telegram_id INTEGER PRIMARY KEY,

                username TEXT,

                created_at TEXT
                DEFAULT CURRENT_TIMESTAMP

            )
            """
        )



        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS records (

                id INTEGER PRIMARY KEY AUTOINCREMENT,


                user_id INTEGER NOT NULL,

                record_date TEXT NOT NULL,

                count INTEGER NOT NULL
                CHECK(count >= 0),


                FOREIGN KEY(user_id)
                REFERENCES users(telegram_id)

                ON DELETE CASCADE,


                UNIQUE(
                    user_id,
                    record_date
                )

            )
            """
        )



        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (

                user_id INTEGER NOT NULL,

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



    # =========================================================
    # USERS
    # =========================================================


    def create_user(
        self,
        telegram_id,
        username=None
    ):

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
                    username
                )
            )



    def user_exists(
        self,
        telegram_id
    ):

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
                )
            )

            return cursor.fetchone() is not None



    # =========================================================
    # RECORDS
    # =========================================================


    def add_or_update_record(
        self,
        user_id,
        record_date,
        count
    ):

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
                    count
                )
            )



    def get_record(
        self,
        user_id,
        record_date
    ):

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
                    record_date.isoformat()
                )
            )


            row = cursor.fetchone()


            return None if row is None else row["count"]



    def get_records(
        self,
        user_id
    ):

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
                )
            )


            records = {}


            for row in cursor.fetchall():

                records[
                    date.fromisoformat(
                        row["record_date"]
                    )
                ] = row["count"]


            return records



    def delete_record(
        self,
        user_id,
        record_date
    ):

        with self.connection() as connection:

            cursor = connection.execute(
                """
                DELETE FROM records

                WHERE user_id = ?

                AND record_date = ?

                """,
                (
                    user_id,
                    record_date.isoformat()
                )
            )


            if cursor.rowcount == 0:

                raise ValueError(
                    "Record does not exist."
                )


            return True



    # =========================================================
    # SETTINGS
    # =========================================================


    def get_setting(
        self,
        user_id,
        setting_key
    ):

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
                    setting_key
                )
            )


            row = cursor.fetchone()


            return (
                None
                if row is None
                else row["setting_value"]
            )



    def set_setting(
        self,
        user_id,
        setting_key,
        setting_value
    ):

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
                    setting_value
                )
            )