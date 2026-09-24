from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import config
from database import TrackerDatabase
from timezone import DEFAULT_TIMEZONE, get_today

USER_ID_REQUIRED_MESSAGE = "user_id cannot be None."
USER_ID_BOOL_MESSAGE = "user_id cannot be boolean."
USER_ID_TYPE_MESSAGE = "user_id must be an integer."
DATE_TYPE_MESSAGE = "record_date must be a datetime.date object."
COUNT_TYPE_MESSAGE = "count must be an integer."
COUNT_NEGATIVE_MESSAGE = "count cannot be negative."
COUNT_TOO_HIGH_MESSAGE = "count cannot exceed 1000."
FUTURE_DATE_MESSAGE = "Record date cannot be in the future."
RECORD_DECRYPTION_MESSAGE = (
    "Stored record data could not be decrypted. "
    "Please restore the database backup or contact support."
)

DEFAULT_RATE_LIMITS = {
    "graph_generation": {"limit": 5, "window_seconds": 60},
    "export_generation": {"limit": 2, "window_seconds": 60},
}


class TrackerLogic:
    """
    Application logic for the tracker.

    This class contains validation and business rules.
    It does not know anything about Telegram.
    """

    def __init__(self, db_path: str | None = None) -> None:
        # Prefer explicit injection of a db_path. If not provided, fall
        # back to the application configuration. This makes tests simpler
        # and avoids scattering os.getenv throughout business logic.
        resolved_path = db_path or config.DATABASE_PATH
        self.database = TrackerDatabase(resolved_path)


    # =========================================================
    # USERS
    # =========================================================

    def create_user(
        self,
        user_id: int,
        username: str | None = None,
    ) -> None:

        self._validate_user_id(user_id)

        self.database.create_user(
            user_id,
            username
        )

        # No in-memory cache: rely on the database as the source of truth.

        timezone = self.database.get_setting(
            user_id,
            "timezone"
        )

        if timezone is None:

            self.database.set_setting(
                user_id,
                "timezone",
                DEFAULT_TIMEZONE
            )


    def user_exists(
        self,
        user_id: int,
    ) -> bool:

        self._validate_user_id(user_id)

        # Query the database directly. This keeps behavior simple and
        # avoids subtle cache-staleness concerns across handler lifecycles.
        return self.database.user_exists(user_id)


    # =========================================================
    # RECORDS
    # =========================================================

    def save_record(
        self,
        user_id: int,
        record_date: date,
        count: int,
    ) -> None:

        self._validate_user_id(user_id)

        self._validate_record_date(
        user_id,
        record_date
        )

        self._validate_count(count)

        # Use a single-connection DB operation to validate user and write
        # the record atomically, reducing connection churn under load.
        self.database.add_or_update_record_require_user(
            user_id,
            record_date,
            count,
        )


    def delete_record(
        self,
        user_id: int,
        record_date: date,
    ) -> bool:

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

    def delete_user(
        self,
        user_id: int,
    ) -> bool:

        self._validate_user_id(user_id)
        self._require_user(user_id)

        deleted = self.database.delete_user(user_id)

        if not deleted:
            raise ValueError("User does not exist.")

        # No cache to invalidate; database is authoritative.

        return True


    def get_record(
        self,
        user_id: int,
        record_date: date,
    ) -> int | None:

        self._validate_user_id(user_id)
        self._validate_date(record_date)

        self._require_user(user_id)

        return self.database.get_record(
            user_id,
            record_date
        )


    def get_records(
        self,
        user_id: int,
    ) -> dict[date, int]:

        self._validate_user_id(user_id)

        self._require_user(user_id)

        return self.database.get_records(
            user_id
        )


    # =========================================================
    # STATISTICS
    # =========================================================

    def get_statistics(self, user_id: int) -> dict[str, int | float]:

        records = self.get_records(user_id)

        if not records:
            return {
                "days": 0,
                "total": 0,
                "average": 0,
                "highest": 0,
            }

        values = records.values()

        return {
            "days": len(records),
            "total": sum(values),
            "average": sum(values) / len(records),
            "highest": max(values),
        }

    # =========================================================
    # RATE LIMITS
    # =========================================================

    def check_rate_limit(
        self,
        user_id: int,
        operation: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> bool:
        self._validate_user_id(user_id)

        config = DEFAULT_RATE_LIMITS.get(operation, {})
        resolved_limit = config.get("limit") if limit is None else limit
        resolved_window = config.get("window_seconds") if window_seconds is None else window_seconds

        if resolved_limit is None or resolved_window is None:
            return True

        if resolved_limit <= 0:
            return True

        return self.database.check_and_record_rate_limit(
            user_id,
            operation,
            int(resolved_limit),
            int(resolved_window),
        )

    # =========================================================
    # SETTINGS
    # =========================================================

    def get_setting(
        self,
        user_id: int,
        setting_key: str,
        default: object | None = None,
    ) -> object | None:

        self._validate_user_id(user_id)

        if not self.user_exists(user_id):
            return default

        value = self.database.get_setting(
            user_id,
            setting_key
        )

        if value is None:
            return default

        return value


    def set_setting(
        self,
        user_id: int,
        setting_key: str,
        setting_value: object,
    ) -> None:

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
        user_id: int | None,
    ) -> None:

        if user_id is None:
            raise ValueError(USER_ID_REQUIRED_MESSAGE)

        if isinstance(user_id, bool):
            raise TypeError(USER_ID_BOOL_MESSAGE)

        if not isinstance(user_id, int):
            raise TypeError(USER_ID_TYPE_MESSAGE)

    def _validate_date(
        self,
        record_date: date,
    ) -> None:

        if not isinstance(record_date, date):
            raise TypeError(DATE_TYPE_MESSAGE)

    def _validate_timezone_name(self, timezone_name: str | None) -> str:
        if timezone_name is None:
            return DEFAULT_TIMEZONE

        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ZoneInfoNotFoundError(
                f"Unknown timezone: {timezone_name}"
            ) from exc

        return timezone_name

    def _resolve_user_timezone(self, user_id: int) -> str:
        timezone_name = self.get_setting(
            user_id,
            "timezone",
            DEFAULT_TIMEZONE,
        )
        return self._validate_timezone_name(timezone_name)

    # =========================================================
    # PERSISTED USER STATE
    # =========================================================

    def set_user_state(self, user_id: int, state_key: str, state_value: object) -> None:
        self._validate_user_id(user_id)
        self._require_user(user_id)
        self.database.set_user_state(user_id, state_key, state_value)

    def get_user_state(self, user_id: int, state_key: str) -> object | None:
        self._validate_user_id(user_id)
        # do not require user here; reading state for unknown user should
        # simply return None
        return self.database.get_user_state(user_id, state_key)

    def delete_user_state(self, user_id: int, state_key: str) -> None:
        self._validate_user_id(user_id)
        self.database.delete_user_state(user_id, state_key)

    def _validate_record_date(
        self,
        user_id: int,
        record_date: date,
    ) -> None:

        self._validate_date(record_date)
        timezone_name = self._resolve_user_timezone(user_id)

        if record_date > get_today(timezone_name):
            raise ValueError(FUTURE_DATE_MESSAGE)

    def _validate_count(
        self,
        count: int,
    ) -> None:

        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError(COUNT_TYPE_MESSAGE)

        if count < 0:
            raise ValueError(COUNT_NEGATIVE_MESSAGE)

        if count > 1000:
            raise ValueError(COUNT_TOO_HIGH_MESSAGE)

    def _require_user(
        self,
        user_id: int,
    ) -> None:

        if not self.user_exists(user_id):
            raise ValueError(
                "User does not exist."
            )