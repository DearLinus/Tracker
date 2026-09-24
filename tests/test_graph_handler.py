"""
Unit tests for the graph handler (show_graph_menu / send_graph).

Everything the handler talks to is replaced with a fake:
  - create_graph, get_graph_theme, get_user_id, get_user_today, reset_state
  - Telegram's update / context (MagicMock + AsyncMock)

So these tests only check the handler's own logic: which messages it sends,
which arguments it passes on, and how it behaves on errors.

Adjust the import below if your handler lives in a different module.
"""

import logging
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import InputFile

import handlers.graph as gh  # <-- change if your module name differs
from handlers.constants import GRAPH_TIMELINE, GRAPH_TIMELINES
from keyboards import GRAPH_KEYBOARD, MAIN_KEYBOARD

pytestmark = pytest.mark.asyncio

VALID_TIMELINE = next(iter(GRAPH_TIMELINES))
PNG_BYTES = b"\x89PNG-fake-image-bytes"
TODAY = date(2026, 9, 19)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def make_image():
    """A fake graph image whose read position is at the END,
    like a freshly saved BytesIO (the handler must seek(0) itself)."""
    image = BytesIO(PNG_BYTES)
    image.seek(0, 2)
    return image


@pytest.fixture
def events():
    """Ordered log of what the handler did."""
    return []


@pytest.fixture
def update(events):
    upd = MagicMock()

    async def reply_text(text, **kwargs):
        events.append(("text", text))

    async def reply_photo(**kwargs):
        events.append(("photo", None))

    upd.message.reply_text = AsyncMock(side_effect=reply_text)
    upd.message.reply_photo = AsyncMock(side_effect=reply_photo)
    return upd


@pytest.fixture
def context():
    ctx = MagicMock()
    ctx.user_data = {"stale_key": "stale_value"}
    return ctx


@pytest.fixture
def deps(monkeypatch, events):
    """Replaces every dependency of the handler module."""

    def fake_reset_state(ctx):
        events.append(("reset", None))
        ctx.user_data.clear()

    fake_tracker = object()

    d = SimpleNamespace(
        tracker=fake_tracker,
        reset_state=MagicMock(side_effect=fake_reset_state),
        create_graph=MagicMock(return_value=make_image()),
        get_graph_theme=MagicMock(return_value="dark"),
        get_user_id=MagicMock(return_value=42),
        get_user_today=MagicMock(return_value=TODAY),
    )

    monkeypatch.setattr(gh, "get_tracker", lambda ctx: d.tracker)
    monkeypatch.setattr(gh, "reset_state", d.reset_state)
    monkeypatch.setattr(gh, "create_graph", d.create_graph)
    monkeypatch.setattr(gh, "get_graph_theme", d.get_graph_theme)
    monkeypatch.setattr(gh, "get_user_id", d.get_user_id)
    monkeypatch.setattr(gh, "get_user_today", d.get_user_today)

    return d


# ------------------------------------------------------------------
# show_graph_menu
# ------------------------------------------------------------------


async def test_menu_sets_awaiting_state(update, context, deps):
    await gh.show_graph_menu(update, context)

    assert context.user_data["awaiting"] == GRAPH_TIMELINE


async def test_menu_resets_old_state_first(update, context, deps):
    """reset_state must run BEFORE 'awaiting' is set, otherwise it would
    wipe the state we just set."""
    await gh.show_graph_menu(update, context)

    deps.reset_state.assert_called_once_with(context)
    assert "stale_key" not in context.user_data
    assert context.user_data["awaiting"] == GRAPH_TIMELINE


async def test_menu_sends_graph_keyboard(update, context, deps):
    await gh.show_graph_menu(update, context)

    update.message.reply_text.assert_awaited_once()
    kwargs = update.message.reply_text.call_args.kwargs
    assert kwargs["reply_markup"] is GRAPH_KEYBOARD


# ------------------------------------------------------------------
# send_graph: invalid timeline
# ------------------------------------------------------------------


async def test_invalid_timeline_shows_warning(update, context, deps):
    await gh.send_graph(update, context, "Not A Real Range")

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert "available" in args[0]
    assert kwargs["reply_markup"] is GRAPH_KEYBOARD


async def test_invalid_timeline_does_not_build_graph(update, context, deps):
    await gh.send_graph(update, context, "Not A Real Range")

    deps.create_graph.assert_not_called()
    update.message.reply_photo.assert_not_called()


async def test_invalid_timeline_keeps_state(update, context, deps):
    """The user is still choosing a range, so the state must stay."""
    context.user_data["awaiting"] = GRAPH_TIMELINE

    await gh.send_graph(update, context, "Not A Real Range")

    deps.reset_state.assert_not_called()
    assert context.user_data["awaiting"] == GRAPH_TIMELINE


# ------------------------------------------------------------------
# send_graph: success
# ------------------------------------------------------------------


async def test_create_graph_receives_correct_arguments(update, context, deps):
    await gh.send_graph(update, context, VALID_TIMELINE)

    deps.create_graph.assert_called_once_with(
        deps.tracker,
        user_id=42,
        timeline=VALID_TIMELINE,
        theme="dark",
        today=TODAY,
    )


async def test_user_id_theme_and_today_come_from_update(update, context, deps):
    await gh.send_graph(update, context, VALID_TIMELINE)

    deps.get_user_id.assert_called_once_with(update)
    deps.get_graph_theme.assert_called_once_with(update, context)
    deps.get_user_today.assert_called_once_with(update, context)


async def test_photo_is_sent_with_correct_filename(update, context, deps):
    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_photo.assert_awaited_once()
    photo = update.message.reply_photo.call_args.kwargs["photo"]

    assert isinstance(photo, InputFile)
    assert photo.filename == "masturbation_trend.png"


async def test_image_is_rewound_before_sending(update, context, deps):
    """
    Regression: InputFile reads the stream when it is created.
    If the handler forgets seek(0), the photo would be sent EMPTY,
    because the image's position is at the end after savefig().
    """
    await gh.send_graph(update, context, VALID_TIMELINE)

    photo = update.message.reply_photo.call_args.kwargs["photo"]
    assert photo.input_file_content == PNG_BYTES


async def test_caption_contains_timeline_and_theme(update, context, deps):
    deps.get_graph_theme.return_value = "light"

    await gh.send_graph(update, context, VALID_TIMELINE)

    caption = update.message.reply_photo.call_args.kwargs["caption"]
    assert f"Time range: {VALID_TIMELINE}" in caption
    assert "Theme: Light" in caption


async def test_success_resets_state(update, context, deps):
    context.user_data["awaiting"] = GRAPH_TIMELINE

    await gh.send_graph(update, context, VALID_TIMELINE)

    deps.reset_state.assert_called_once_with(context)
    assert context.user_data == {}


async def test_graph_state_clear_is_offloaded_to_thread(
    update, context, deps, monkeypatch
):
    thread_calls = []

    async def fake_to_thread(func, *args, **kwargs):
        thread_calls.append(func)
        return func(*args, **kwargs)

    monkeypatch.setattr(gh.asyncio, "to_thread", fake_to_thread)

    await gh.send_graph(update, context, VALID_TIMELINE)

    assert any(
        getattr(call, "func", None) is gh.clear_user_state for call in thread_calls
    )


async def test_success_sends_main_keyboard_after_photo(update, context, deps, events):
    await gh.send_graph(update, context, VALID_TIMELINE)

    kinds = [kind for kind, _ in events]
    assert kinds.index("photo") < kinds.index("text")

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert args[0] == "Choose another option:"
    assert kwargs["reply_markup"] is MAIN_KEYBOARD


@pytest.mark.parametrize("timeline", list(GRAPH_TIMELINES))
async def test_every_available_timeline_is_accepted(update, context, deps, timeline):
    await gh.send_graph(update, context, timeline)

    deps.create_graph.assert_called_once()
    update.message.reply_photo.assert_awaited_once()


# ------------------------------------------------------------------
# send_graph: no records
# ------------------------------------------------------------------


async def test_no_records_shows_message_with_main_keyboard(update, context, deps):
    deps.create_graph.return_value = None

    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert "No records" in args[0]
    assert kwargs["reply_markup"] is MAIN_KEYBOARD


async def test_no_records_sends_no_photo(update, context, deps):
    deps.create_graph.return_value = None

    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_photo.assert_not_called()


async def test_no_records_resets_state(update, context, deps):
    deps.create_graph.return_value = None
    context.user_data["awaiting"] = GRAPH_TIMELINE

    await gh.send_graph(update, context, VALID_TIMELINE)

    deps.reset_state.assert_called_once_with(context)
    assert context.user_data == {}


async def test_empty_range_shows_informative_message(update, context, deps):
    """When the user has records but none fall into the requested range,
    the handler should inform the user that the selected range is empty.
    """
    deps.create_graph.return_value = "empty_range"

    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert "none in the selected time range" in args[0]
    assert kwargs["reply_markup"] is MAIN_KEYBOARD


# ------------------------------------------------------------------
# send_graph: errors
# ------------------------------------------------------------------


async def test_graph_failure_shows_error_message(update, context, deps):
    deps.create_graph.side_effect = RuntimeError("boom")

    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert "couldn't generate" in args[0]
    assert kwargs["reply_markup"] is MAIN_KEYBOARD


async def test_graph_decryption_failure_shows_decryption_message(update, context, deps):
    from database import RecordDecryptionError
    from logic import RECORD_DECRYPTION_MESSAGE

    deps.create_graph.side_effect = RecordDecryptionError("bad key")

    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert args[0] == RECORD_DECRYPTION_MESSAGE
    assert kwargs["reply_markup"] is MAIN_KEYBOARD


async def test_graph_failure_does_not_raise(update, context, deps):
    deps.create_graph.side_effect = RuntimeError("boom")

    # must swallow the exception, not crash the bot
    await gh.send_graph(update, context, VALID_TIMELINE)


async def test_graph_failure_resets_state(update, context, deps):
    deps.create_graph.side_effect = RuntimeError("boom")
    context.user_data["awaiting"] = GRAPH_TIMELINE

    await gh.send_graph(update, context, VALID_TIMELINE)

    deps.reset_state.assert_called_once_with(context)
    assert context.user_data == {}


async def test_graph_failure_is_logged(update, context, deps, caplog):
    deps.create_graph.side_effect = RuntimeError("boom")

    with caplog.at_level(logging.ERROR):
        await gh.send_graph(update, context, VALID_TIMELINE)

    assert "Failed to generate graph" in caplog.text


async def test_graph_failure_sends_no_photo(update, context, deps):
    deps.create_graph.side_effect = RuntimeError("boom")

    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_photo.assert_not_called()


async def test_telegram_send_failure_shows_error_message(update, context, deps):
    """If sending the photo itself fails (network, size...), the user
    should still get an error message instead of silence."""
    update.message.reply_photo.side_effect = RuntimeError("telegram down")

    await gh.send_graph(update, context, VALID_TIMELINE)

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.call_args
    assert "couldn't generate" in args[0]
    assert kwargs["reply_markup"] is MAIN_KEYBOARD
    deps.reset_state.assert_called_once_with(context)
