import sqlite3
from datetime import date


class TrackerDatabase:
    """
    Handles all SQLite operations.

    This class knows about SQL and the database.
    The GUI and business logic do not need to know SQL details.
    """

    def __init__(self, db_path="tracker.db"):
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        self._create_table()

    def _create_table(self):
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                record_date TEXT PRIMARY KEY,
                count INTEGER NOT NULL CHECK (count >= 0)
            )
            """
        )
        self.connection.commit()

    def add_or_update_record(self, record_date, count):
        self.connection.execute(
            """
            INSERT INTO records (record_date, count)
            VALUES (?, ?)
            ON CONFLICT(record_date)
            DO UPDATE SET count = excluded.count
            """,
            (record_date.isoformat(), count)
        )
        self.connection.commit()

    def update_record(self, old_date, new_date, count):
        """Update a record's date and count in one database transaction."""
        if old_date == new_date:
            self.connection.execute(
                "UPDATE records SET count = ? WHERE record_date = ?",
                (count, old_date.isoformat())
            )
        else:
            self.connection.execute(
                """
                UPDATE records
                SET record_date = ?, count = ?
                WHERE record_date = ?
                """,
                (new_date.isoformat(), count, old_date.isoformat())
            )
        self.connection.commit()

    def delete_record(self, record_date):
        cursor = self.connection.execute(
            "DELETE FROM records WHERE record_date = ?",
            (record_date.isoformat(),)
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def get_record(self, record_date):
        cursor = self.connection.execute(
            "SELECT count FROM records WHERE record_date = ?",
            (record_date.isoformat(),)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return row[0]

    def get_records(self):
        cursor = self.connection.execute(
            """
            SELECT record_date, count
            FROM records
            ORDER BY record_date ASC
            """
        )
        records = {}
        for record_date, count in cursor.fetchall():
            records[date.fromisoformat(record_date)] = count
        return records

    def close(self):
        self.connection.close()