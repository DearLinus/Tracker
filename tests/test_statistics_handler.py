import pytest

from handlers.statistics import show_statistics


class FakeUser:
    def __init__(self):
        self.id = 123
        self.username = "test_user"


class FakeMessage:

    def __init__(self):
        self.replies = []


    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:

    def __init__(self):
        self.effective_user = FakeUser()
        self.message = FakeMessage()


class FakeContext:

    def __init__(self):
        self.user_data = {
            "awaiting": "something"
        }



# =========================================================
# empty statistics
# =========================================================


@pytest.mark.asyncio
async def test_statistics_without_records(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    monkeypatch.setattr(
        "handlers.statistics.tracker.get_records",
        lambda *args: {}
    )


    await show_statistics(
        update,
        context
    )


    assert len(
        update.message.replies
    ) == 1


    assert (
        "don't have any records"
        in update.message.replies[0]
    )


    assert (
        "awaiting"
        not in context.user_data
    )



# =========================================================
# statistics calculation
# =========================================================


@pytest.mark.asyncio
async def test_statistics_calculates_values(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    monkeypatch.setattr(
        "handlers.statistics.tracker.get_records",
        lambda *args: {
            "2026-09-10": 5,
            "2026-09-11": 10,
            "2026-09-12": 15,
        }
    )


    await show_statistics(
        update,
        context
    )


    message = update.message.replies[0]


    assert (
        "Recorded days: 3"
        in message
    )

    assert (
        "Total: 30"
        in message
    )

    assert (
        "Average: 10.00"
        in message
    )

    assert (
        "Highest: 15"
        in message
    )


    assert (
        "awaiting"
        not in context.user_data
    )

# =========================================================
# user isolation
# =========================================================


@pytest.mark.asyncio
async def test_statistics_uses_correct_user_id(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()

    received_ids = []


    def fake_get_records(user_id):

        received_ids.append(
            user_id
        )

        return {
            "2026-09-10": 5
        }


    monkeypatch.setattr(
        "handlers.statistics.tracker.get_records",
        fake_get_records
    )


    await show_statistics(
        update,
        context
    )


    assert received_ids == [
        123
    ]