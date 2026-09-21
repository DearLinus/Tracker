import pytest

from handlers.router import handle_text
from handlers.constants import TODAY_RECORD_BUTTON


class FakeUser:
    def __init__(self):
        self.id = 123
        self.username = "test_user"


class FakeMessage:

    def __init__(self, text):
        self.text = text
        self.replies = []


    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:

    def __init__(self, text):
        self.effective_user = FakeUser()
        self.message = FakeMessage(text)


class FakeContext:

    def __init__(self):
        self.user_data = {}



# =========================================================
# user validation
# =========================================================


@pytest.mark.asyncio
async def test_router_rejects_unknown_user(monkeypatch):

    update = FakeUpdate("anything")
    context = FakeContext()


    class FakeTrackerA:
        @staticmethod
        def user_exists(user_id):
            return False

    monkeypatch.setattr("handlers.router.get_tracker", lambda ctx: FakeTrackerA(), raising=True)


    await handle_text(
        update,
        context
    )


    assert (
        "Please start the bot first"
        in update.message.replies[0]
    )



# =========================================================
# today record button
# =========================================================


@pytest.mark.asyncio
async def test_router_calls_today_record(monkeypatch):

    update = FakeUpdate(
        TODAY_RECORD_BUTTON
    )
    context = FakeContext()


    class FakeTrackerB:
        @staticmethod
        def user_exists(user_id):
            return True

    monkeypatch.setattr("handlers.router.get_tracker", lambda ctx: FakeTrackerB(), raising=True)


    called = []


    async def fake_start_today(update, context):
        called.append(True)


    monkeypatch.setattr(
        "handlers.router.start_today_record",
        fake_start_today
    )


    await handle_text(
        update,
        context
    )


    assert called == [True]



# =========================================================
# today count state
# =========================================================


@pytest.mark.asyncio
async def test_router_saves_today_record_when_waiting(monkeypatch):

    update = FakeUpdate(
        "8"
    )

    context = FakeContext()

    context.user_data["awaiting"] = "today_count"


    class FakeTrackerC:
        @staticmethod
        def user_exists(user_id):
            return True

    monkeypatch.setattr("handlers.router.get_tracker", lambda ctx: FakeTrackerC(), raising=True)


    called = []


    async def fake_save_today(update, context):
        called.append(True)


    monkeypatch.setattr(
        "handlers.router.save_today_record",
        fake_save_today
    )


    await handle_text(
        update,
        context
    )


    assert called == [True]


@pytest.mark.asyncio
async def test_router_allows_menu_action_while_waiting(monkeypatch):

    update = FakeUpdate("📈 Graph")
    context = FakeContext()
    context.user_data["awaiting"] = "today_count"

    class FakeTrackerD:
        @staticmethod
        def user_exists(user_id):
            return True

    monkeypatch.setattr("handlers.router.get_tracker", lambda ctx: FakeTrackerD(), raising=True)

    called = []

    async def fake_show_graph_menu(update, context):
        called.append(True)

    monkeypatch.setattr(
        "handlers.router.show_graph_menu",
        fake_show_graph_menu
    )

    await handle_text(update, context)

    assert called == [True]