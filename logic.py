from datetime import date

from database import TrackerDatabase
from timezone import today as get_today, DEFAULT_TIMEZONE


class TrackerLogic:
    """
    Application logic for the tracker.

    This class contains validation and business rules.
    It does not know anything about Telegram.
    """

    def __init__(self, db_path="tracker.db"):
        self.database = TrackerDatabase(db_path)


    # =========================================================
    # USERS
    # =========================================================

    def create_user(
        self,
        user_id,
        username=None
    ):

        self._validate_user_id(user_id)

        self.database.create_user(
            user_id,
            username
        )

        self.database.set_setting(
            user_id,
            "timezone",
            "Asia/Tehran"
        )


    def user_exists(
        self,
        user_id
    ):

        self._validate_user_id(user_id)

        return self.database.user_exists(
            user_id
        )


    # =========================================================
    # RECORDS
    # =========================================================

    def save_record(
        self,
        user_id,
        record_date,
        count
    ):

        self._validate_user_id(user_id)

        self._validate_record_date(
        user_id,
        record_date
        )

        self._validate_count(count)

        self._require_user(user_id)

        self.database.add_or_update_record(
            user_id,
            record_date,
            count
        )


    def update_record(
        self,
        user_id,
        record_date,
        count
    ):

        self._validate_user_id(user_id)

        self._validate_record_date(
        user_id,
        record_date
        )
        
        self._validate_count(count)

        self._require_user(user_id)

        old_record = self.database.get_record(
            user_id,
            record_date
        )

        if old_record is None:
            raise ValueError(
                "The record you are trying to edit does not exist."
            )

        self.database.add_or_update_record(
            user_id,
            record_date,
            count
        )


    def delete_record(
        self,
        user_id,
        record_date
    ):

        self._validate_user_id(user_id)
        self._validate_date(record_date)

        self._require_user(user_id)

        deleted = self.database.delete_record(
            user_id,
            record_date
        )

        if not deleted:
            raise ValueError(
                "The record you are trying to delete does not exist."
            )

        return deleted


    def get_record(
        self,
        user_id,
        record_date
    ):

        self._validate_user_id(user_id)
        self._validate_date(record_date)

        self._require_user(user_id)

        return self.database.get_record(
            user_id,
            record_date
        )


    def get_records(
        self,
        user_id
    ):

        self._validate_user_id(user_id)

        self._require_user(user_id)

        return self.database.get_records(
            user_id
        )


    # =========================================================
    # STATISTICS
    # =========================================================

    def get_total(
        self,
        user_id
    ):

        records = self.get_records(user_id)

        return sum(
            records.values()
        )


    def get_average(
        self,
        user_id
    ):

        records = self.get_records(user_id)

        if not records:
            return 0

        return sum(
            records.values()
        ) / len(records)


    def get_highest(
        self,
        user_id
    ):

        records = self.get_records(user_id)

        if not records:
            return 0

        return max(
            records.values()
        )


    # =========================================================
    # SETTINGS
    # =========================================================

    def get_setting(
        self,
        user_id,
        setting_key,
        default=None
    ):

        self._validate_user_id(user_id)
        self._require_user(user_id)

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

        self._validate_user_id(user_id)
        self._require_user(user_id)

        self.database.set_setting(
            user_id,
            setting_key,
            setting_value
        )


    # =========================================================
    # VALIDATION
    # =========================================================

    def _validate_user_id(
        self,
        user_id
    ):

        if user_id is None:
            raise ValueError(
                "user_id cannot be None."
            )

        if isinstance(user_id, bool):
            raise TypeError(
                "user_id cannot be boolean."
            )

        if not isinstance(user_id, int):
            raise TypeError(
                "user_id must be an integer."
            )


    def _validate_date(
        self,
        record_date
    ):

        if not isinstance(record_date, date):
            raise TypeError(
                "record_date must be a datetime.date object."
            )


    def _validate_record_date(
        self,
        user_id,
        record_date
    ):

        self._validate_date(record_date)
        timezone = self.get_setting(
        user_id,
        "timezone",
        DEFAULT_TIMEZONE
        )

        if record_date > get_today(timezone):
        
            raise ValueError(
                "Record date cannot be in the future."
            )


    def _validate_count(
        self,
        count
    ):

        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError(
                "count must be an integer."
            )

        if count < 0:
            raise ValueError(
                "count cannot be negative."
            )


    def _require_user(
        self,
        user_id
    ):

        if not self.database.user_exists(user_id):
            raise ValueError(
                "User does not exist."
            )