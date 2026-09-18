import pytest

from handlers.records import (
    start_today_record,
    save_today_record,
    start_new_record,
    save_new_record,
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



# =========================================================
# start_today_record
# =========================================================


@pytest.mark.asyncio
async def test_start_today_record_sets_state(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    monkeypatch.setattr(
        "handlers.records.tracker.get_record",
        lambda *args: None
    )

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

    monkeypatch.setattr(
        "handlers.records.tracker.get_record",
        lambda *args: 5
    )

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


    monkeypatch.setattr(
        "handlers.records.tracker.get_record",
        lambda *args: None
    )


    def fake_save(
        user_id,
        record_date,
        count
    ):
        saved.append(
            (
                user_id,
                count
            )
        )


    monkeypatch.setattr(
        "handlers.records.tracker.save_record",
        fake_save
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


    monkeypatch.setattr(
        "handlers.records.tracker.get_record",
        lambda *args: None
    )


    monkeypatch.setattr(
        "handlers.records.tracker.save_record",
        lambda user_id, date, count:
            saved.append(count)
    )


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