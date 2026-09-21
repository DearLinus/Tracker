import pytest

from handlers.records import (
    start_today_record,
    save_today_record,
    start_new_record,
    save_new_record,
)
import sqlite3
from zoneinfo import ZoneInfoNotFoundError
from handlers.constants import (
    NEGATIVE_COUNT_MESSAGE,
    INVALID_DATE_MESSAGE,
    COUNT_MUST_BE_WHOLE_NUMBER_MESSAGE,
    GENERIC_RECORD_ERROR_MESSAGE,
)


class FakeUser:
    def __init__(self):
        self.id = 123
        self.username = "test_user"


class FakeMessage:

    def __init__(self, text=None):
        self.text = text
        self.replies = []


    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:

    def __init__(self, text=None):
        self.effective_user = FakeUser()
        self.message = FakeMessage(text)


class FakeContext:

    def __init__(self):
        self.user_data = {}
        self.bot_data = {}



# =========================================================
# start_today_record
# =========================================================


@pytest.mark.asyncio
async def test_start_today_record_sets_state(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    class FakeTracker1:
        @staticmethod
        def get_record(*args):
            return None
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker1())}

    await start_today_record(
        update,
        context
    )

    assert (
        context.user_data["awaiting"]
        ==
        "today_count"
    )

    assert len(
        update.message.replies
    ) == 1



@pytest.mark.asyncio
async def test_start_today_record_existing_record(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    class FakeTracker2:
        @staticmethod
        def get_record(*args):
            return 5
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker2())}

    await start_today_record(
        update,
        context
    )

    assert (
        "5"
        in update.message.replies[0]
    )



# =========================================================
# save_today_record
# =========================================================


@pytest.mark.asyncio
async def test_save_today_record_creates_record(monkeypatch):

    update = FakeUpdate(
        "8"
    )

    context = FakeContext()

    saved = []


    class FakeTracker3:
        @staticmethod
        def get_record(*args):
            return None

        @staticmethod
        def save_record(user_id, record_date, count):
            saved.append((user_id, count))
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    from tests.helpers import autospec_tracker

    fake = FakeTracker3()
    context.bot_data = {"tracker": autospec_tracker(fake)}


    async def fake_send_sticker(*args, **kwargs):
        pass


    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker
    )


    async def fake_send_sticker(*args, **kwargs):
        pass


    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker
    )


    await save_today_record(
        update,
        context
    )


    assert saved == [
        (123, 8)
    ]

    assert (
        "awaiting"
        not in context.user_data
    )



@pytest.mark.asyncio
async def test_save_today_record_rejects_invalid_number():

    update = FakeUpdate(
        "abc"
    )

    context = FakeContext()


    await save_today_record(
        update,
        context
    )


    assert (
        "whole number"
        in update.message.replies[0]
    )



# =========================================================
# start_new_record
# =========================================================


@pytest.mark.asyncio
async def test_start_new_record_sets_state():

    update = FakeUpdate()
    context = FakeContext()

    # provide a minimal tracker that implements state persistence used by the handler
    class _StateTracker:
        @staticmethod
        def set_user_state(user_id, key, value):
            return None

    context.bot_data["tracker"] = _StateTracker()

    await start_new_record(
        update,
        context
    )


    assert (
        context.user_data["awaiting"]
        ==
        "new_record"
    )



# =========================================================
# save_new_record
# =========================================================


@pytest.mark.asyncio
async def test_save_new_record_creates_record(monkeypatch):

    update = FakeUpdate(
        "2026-09-10 8"
    )

    context = FakeContext()

    saved = []


    class FakeTracker4:
        @staticmethod
        def get_record(*args):
            return None

        @staticmethod
        def save_record(user_id, date, count):
            saved.append(count)
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    fake = FakeTracker4()
    context.bot_data = {"tracker": fake}


    async def fake_send_sticker(*args, **kwargs):
        pass


    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker
    )


    await save_new_record(
        update,
        context
    )


    assert saved == [8]

@pytest.mark.asyncio
async def test_save_new_record_invalid_format():

    update = FakeUpdate(
        "wrong"
    )

    context = FakeContext()


    await save_new_record(
        update,
        context
    )


    assert (
        "Invalid format"
        in update.message.replies[0]
        )


@pytest.mark.asyncio
async def test_save_today_record_negative_count():

    update = FakeUpdate(
        "-3"
    )

    context = FakeContext()

    # minimal tracker to satisfy handler lookup
    class FakeTracker:
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    await save_today_record(
        update,
        context
    )

    assert NEGATIVE_COUNT_MESSAGE in update.message.replies[0]


@pytest.mark.asyncio
async def test_save_new_record_invalid_date_and_count_cases():

    context = FakeContext()

    class FakeTracker:
        @staticmethod
        def get_setting(user_id, key, default=None):
            return default

    from tests.helpers import autospec_tracker

    context.bot_data = {"tracker": autospec_tracker(FakeTracker())}

    # invalid date
    update1 = FakeUpdate("2026-13-01 5")
    await save_new_record(update1, context)
    assert INVALID_DATE_MESSAGE in update1.message.replies[0]

    # non-integer count
    update2 = FakeUpdate("2026-09-10 abc")
    await save_new_record(update2, context)
    assert COUNT_MUST_BE_WHOLE_NUMBER_MESSAGE in update2.message.replies[0]

    # negative count
    update3 = FakeUpdate("2026-09-10 -5")
    await save_new_record(update3, context)
    assert NEGATIVE_COUNT_MESSAGE in update3.message.replies[0]


@pytest.mark.asyncio
async def test_save_today_record_handles_db_error(monkeypatch):

    update = FakeUpdate("8")
    context = FakeContext()

    class BrokenTracker:
        @staticmethod
        def get_record(*args):
            return None

        @staticmethod
        def save_record(*args, **kwargs):
            raise sqlite3.Error("boom")

        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    context.bot_data = {"tracker": BrokenTracker()}

    async def fake_send_sticker(*args, **kwargs):
        pass

    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker
    )

    await save_today_record(update, context)

    assert GENERIC_RECORD_ERROR_MESSAGE in update.message.replies[-1]


@pytest.mark.asyncio
async def test_save_today_record_handles_tracker_value_error(monkeypatch):

    update = FakeUpdate("8")
    context = FakeContext()

    class BadTracker:
        @staticmethod
        def get_record(*args):
            return None

        @staticmethod
        def save_record(*args, **kwargs):
            raise ValueError("validation failed")

        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    context.bot_data = {"tracker": BadTracker()}

    async def fake_send_sticker(*args, **kwargs):
        pass

    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker,
    )

    await save_today_record(update, context)

    assert "validation failed" in update.message.replies[-1]


@pytest.mark.asyncio
async def test_save_new_record_handles_zoneinfo_error(monkeypatch):

    update = FakeUpdate("2026-09-10 5")
    context = FakeContext()

    class BadTracker2:
        @staticmethod
        def get_record(*args):
            return None

        @staticmethod
        def save_record(*args, **kwargs):
            raise ZoneInfoNotFoundError("tz")

        @staticmethod
        def get_setting(user_id, key, default=None):
            return default
        @staticmethod
        def set_user_state(user_id, key, value):
            return None
        @staticmethod
        def get_user_state(user_id, key):
            return None
        @staticmethod
        def delete_user_state(user_id, key):
            return None

    context.bot_data = {"tracker": BadTracker2()}

    async def fake_send_sticker(*args, **kwargs):
        pass

    monkeypatch.setattr(
        "handlers.records.send_sticker_if_available",
        fake_send_sticker,
    )

    await save_new_record(update, context)

    assert "I couldn't save the record" in update.message.replies[-1]