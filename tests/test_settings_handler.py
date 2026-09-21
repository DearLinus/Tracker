import pytest

from handlers.settings import (
    show_settings,
    change_graph_theme,
)


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
        self.user_data = {}



@pytest.mark.asyncio
async def test_show_settings_sets_state(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    monkeypatch.setattr(
        "handlers.settings.get_graph_theme",
        lambda update, context: "dark"
    )


    await show_settings(
        update,
        context
    )


    assert (
        context.user_data["awaiting"]
        ==
        "settings"
    )


    assert (
        "Dark"
        in update.message.replies[0]
    )



@pytest.mark.asyncio
async def test_change_graph_theme_saves_setting(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    saved = []


    class FakeTracker:
        def set_setting(self, user_id, key, value):
            saved.append((user_id, key, value))

    monkeypatch.setattr("handlers.settings.get_tracker", lambda ctx: FakeTracker(), raising=True)


    await change_graph_theme(
        update,
        context,
        "dark"
    )


    assert saved == [
        (
            123,
            "graph_theme",
            "dark"
        )
    ]


    assert (
        "awaiting"
        not in context.user_data
    )


    assert (
        "Dark graph enabled"
        in update.message.replies[0]
    )