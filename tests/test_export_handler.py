from datetime import date

import pytest

from handlers.export import export_records


class FakeUser:
    def __init__(self):
        self.id = 123


class FakeMessage:

    def __init__(self):
        self.replies = []
        self.documents = []


    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


    async def reply_document(self, document, filename=None, **kwargs):
        self.documents.append(
            filename
        )


class FakeUpdate:

    def __init__(self):
        self.effective_user = FakeUser()
        self.message = FakeMessage()


class FakeContext:

    def __init__(self):
        self.user_data = {}
        self.bot_data = {}



@pytest.mark.asyncio
async def test_export_without_records(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    class FakeTracker:
        @staticmethod
        def get_records(user_id):
            return {}
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

    fake = FakeTracker()
    context.bot_data = {"tracker": fake}


    await export_records(
        update,
        context
    )


    assert (
        "No records available"
        in update.message.replies[0]
    )



@pytest.mark.asyncio
async def test_export_creates_file(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    class FakeTracker:
        @staticmethod
        def get_records(user_id):
            return {date(2026, 9, 10): 8}
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

    fake = FakeTracker()
    context.bot_data = {"tracker": fake}


    await export_records(
        update,
        context
    )


    assert (
        "tracker_history.csv"
        in update.message.documents
    )



@pytest.mark.asyncio
async def test_export_uses_correct_user_id(monkeypatch):

    update = FakeUpdate()
    context = FakeContext()


    called = []


    def fake_get_records(user_id):

        called.append(user_id)

        return {}


    class FakeTracker:
        def get_records(self, user_id):
            return fake_get_records(user_id)
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

    fake = FakeTracker()
    context.bot_data = {"tracker": fake}


    await export_records(
        update,
        context
    )


    assert called == [123]