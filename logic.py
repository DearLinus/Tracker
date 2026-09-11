from datetime import date

from database import TrackerDatabase


class TrackerLogic:
    """
    Application logic for the tracker.

    This class contains validation and business rules.
    It does not know anything about Tkinter or Telegram.
    """

    def __init__(self, db_path="tracker.db"):
        self.database = TrackerDatabase(db_path)

    # =========================================================
    # RECORDS
    # =========================================================

    def add_record(self, record_date, count):
        self._validate_date(record_date)
        self._validate_count(count)

        self.database.add_or_update_record(
            record_date,
            count
        )

    def update_record(
        self,
        old_date,
        new_date,
        count
    ):
        self._validate_date(old_date)
        self._validate_date(new_date)
        self._validate_count(count)

        if self.database.get_record(old_date) is None:
            raise ValueError(
                "The record you are trying to edit does not exist."
            )

        if (
            old_date != new_date
            and self.database.get_record(new_date) is not None
        ):
            raise ValueError(
                "A record already exists for the new date."
            )

        self.database.update_record(
            old_date,
            new_date,
            count
        )

    def delete_record(self, record_date):
        self._validate_date(record_date)

        return self.database.delete_record(
            record_date
        )

    def get_record(self, record_date):
        self._validate_date(record_date)

        return self.database.get_record(
            record_date
        )

    def get_records(self):
        return self.database.get_records()

    def get_total(self):
        return sum(
            self.get_records().values()
        )

    def get_average(self):
        records = self.get_records()

        if not records:
            return 0

        return self.get_total() / len(records)

    def get_highest(self):
        records = self.get_records()

        if not records:
            return 0

        return max(records.values())

    # =========================================================
    # SETTINGS
    # =========================================================

    def get_setting(
        self,
        user_id,
        setting_key,
        default=None
    ):
        value = self.database.get_setting(
            user_id,
            setting_key
        )

        if value is None:
            return default

        return value

    def set_setting(
        self,
        user_id,
        setting_key,
        setting_value
    ):
        self.database.set_setting(
            user_id,
            setting_key,
            setting_value
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    def _validate_date(self, record_date):
        if not isinstance(record_date, date):
            raise TypeError(
                "record_date must be a datetime.date object."
            )

    def _validate_count(self, count):
        if not isinstance(count, int):
            raise TypeError(
                "count must be an integer."
            )

        if count < 0:
            raise ValueError(
                "count cannot be negative."
            )

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):
        self.database.close()