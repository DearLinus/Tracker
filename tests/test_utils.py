"""
Unit tests for handlers/utils.py.

The interesting part is get_user_today(): the calendar date depends on the
user's timezone, and create_graph() compares record dates with it. To test
that without waiting for real midnight, datetime.now() is replaced with a
frozen clock.

Adjust the import below if your module lives elsewhere.
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest

import handlers.utils as utils  # <-- change if your module name differs
from handlers import constants


# ------------------------------------------------------------------
# Helpers / fixtures
# ------------------------------------------------------------------

class FakeTracker:
    """Only the part of the tracker that utils.py uses."""

    def __init__(self, settings=None):
        # {(user_id, key): value}
        self.settings = dict(settings or {})
        self.calls = []

    def get_setting(self, user_id, key, default=None):
        self.calls.append((user_id, key))
        return self.settings.get((user_id, key), default)


def make_update(user_id=1):
    update = MagicMock()
    update.effective_user.id = user_id
    return update


@pytest.fixture
def tracker(monkeypatch):
    fake = FakeTracker()
    monkeypatch.setattr(utils, "get_tracker", lambda ctx: fake)
    return fake


@pytest.fixture
def freeze_time(monkeypatch):
    """freeze_time(datetime(..., tzinfo=timezone.utc)) sets 'now'."""

    def _freeze(moment_utc):
        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return moment_utc.astimezone(tz)

        monkeypatch.setattr(utils, "datetime", FrozenDatetime)

    return _freeze


# ------------------------------------------------------------------
# get_user_id
# ------------------------------------------------------------------

def test_get_user_id_returns_effective_user_id():
    assert utils.get_user_id(make_update(user_id=12345)) == 12345


# ------------------------------------------------------------------
# reset_state
# ------------------------------------------------------------------

def test_reset_state_removes_awaiting():
    context = MagicMock()
    context.user_data = {"awaiting": "graph_timeline"}

    utils.reset_state(context)

    assert "awaiting" not in context.user_data


def test_reset_state_keeps_other_keys():
    context = MagicMock()
    context.user_data = {"awaiting": "x", "other": "keep me"}

    utils.reset_state(context)

    assert context.user_data == {"other": "keep me"}


def test_reset_state_without_awaiting_does_not_fail():
    context = MagicMock()
    context.user_data = {}

    utils.reset_state(context)

    assert context.user_data == {}


# ------------------------------------------------------------------
# send_sticker_if_available
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sticker_is_sent_when_id_given():
    update = MagicMock()
    update.message.reply_sticker = AsyncMock()

    await utils.send_sticker_if_available(update, "STICKER_ID")

    update.message.reply_sticker.assert_awaited_once_with("STICKER_ID")


@pytest.mark.asyncio
@pytest.mark.parametrize("sticker_id", [None, ""])
async def test_sticker_not_sent_without_id(sticker_id):
    update = MagicMock()
    update.message.reply_sticker = AsyncMock()

    await utils.send_sticker_if_available(update, sticker_id)

    update.message.reply_sticker.assert_not_called()


@pytest.mark.asyncio
async def test_sticker_failure_is_swallowed():
    """A broken sticker must never break the actual reply flow.
    
    TelegramError during sticker send should be logged but not propagated.
    """
    from telegram.error import TelegramError
    
    update = MagicMock()
    update.message.reply_sticker = AsyncMock(side_effect=TelegramError("boom"))
    
    # Should not raise; sticker failure is swallowed
    await utils.send_sticker_if_available(update, "STICKER_ID")


# ------------------------------------------------------------------
# get_graph_theme
# ------------------------------------------------------------------

def test_graph_theme_defaults_to_dark(tracker):
    assert utils.get_graph_theme(make_update(), MagicMock()) == "dark"


def test_default_theme_is_a_known_theme(tracker):
    assert utils.get_graph_theme(make_update(), MagicMock()) in constants.GRAPH_THEMES


def test_graph_theme_returns_saved_value(tracker):
    tracker.settings[(1, "graph_theme")] = "light"

    assert utils.get_graph_theme(make_update(user_id=1), MagicMock()) == "light"


def test_graph_theme_is_per_user(tracker):
    tracker.settings[(1, "graph_theme")] = "light"
    tracker.settings[(2, "graph_theme")] = "dark"

    assert utils.get_graph_theme(make_update(user_id=1), MagicMock()) == "light"
    assert utils.get_graph_theme(make_update(user_id=2), MagicMock()) == "dark"


def test_graph_theme_reads_the_right_setting_for_the_right_user(tracker):
    utils.get_graph_theme(make_update(user_id=77), MagicMock())

    assert tracker.calls == [(77, "graph_theme")]


# ------------------------------------------------------------------
# get_user_timezone
# ------------------------------------------------------------------

def test_timezone_defaults_to_default_timezone(tracker):
    assert utils.get_user_timezone(make_update(), MagicMock()) == utils.DEFAULT_TIMEZONE


def test_timezone_returns_saved_value(tracker):
    tracker.settings[(1, "timezone")] = "Europe/Amsterdam"

    assert utils.get_user_timezone(make_update(user_id=1), MagicMock()) == "Europe/Amsterdam"


def test_timezone_is_per_user(tracker):
    tracker.settings[(1, "timezone")] = "Europe/Amsterdam"

    assert utils.get_user_timezone(make_update(user_id=1), MagicMock()) == "Europe/Amsterdam"
    assert utils.get_user_timezone(make_update(user_id=2), MagicMock()) == utils.DEFAULT_TIMEZONE


def test_timezone_reads_the_right_setting_for_the_right_user(tracker):
    utils.get_user_timezone(make_update(user_id=77), MagicMock())

    assert tracker.calls == [(77, "timezone")]


def test_default_timezone_is_valid():
    ZoneInfo(utils.DEFAULT_TIMEZONE)  # raises if unknown


def test_default_timezone_matches_constants():
    """DEFAULT_TIMEZONE is defined in two places; they must not drift."""
    assert utils.DEFAULT_TIMEZONE == constants.DEFAULT_TIMEZONE


# ------------------------------------------------------------------
# get_user_today
# ------------------------------------------------------------------

def test_today_returns_a_plain_date(tracker):
    """
    create_graph() compares record dates with `today`. A datetime instead
    of a date would raise TypeError there.
    """
    result = utils.get_user_today(make_update(), MagicMock())

    assert isinstance(result, date)
    assert not isinstance(result, datetime)


# 21:00 UTC on Sep 19 is already Sep 20 in Tehran (UTC+3:30 / +4:30),
# still Sep 19 in Amsterdam and Los Angeles.
LATE_EVENING_UTC = datetime(2026, 9, 19, 21, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "tz_name, expected",
    [
        ("UTC", date(2026, 9, 19)),
        ("Europe/Amsterdam", date(2026, 9, 19)),
        ("America/Los_Angeles", date(2026, 9, 19)),
        ("Asia/Tehran", date(2026, 9, 20)),
        ("Pacific/Auckland", date(2026, 9, 20)),
    ],
)
def test_today_depends_on_user_timezone(tracker, freeze_time, tz_name, expected):
    freeze_time(LATE_EVENING_UTC)
    tracker.settings[(1, "timezone")] = tz_name

    assert utils.get_user_today(make_update(user_id=1), MagicMock()) == expected


def test_today_uses_default_timezone_when_none_saved(tracker, freeze_time):
    freeze_time(LATE_EVENING_UTC)

    expected = LATE_EVENING_UTC.astimezone(
        ZoneInfo(utils.DEFAULT_TIMEZONE)
    ).date()

    assert utils.get_user_today(make_update(), MagicMock()) == expected
    assert expected == date(2026, 9, 20)  # Tehran is past midnight already


def test_two_users_can_have_different_today(tracker, freeze_time):
    freeze_time(LATE_EVENING_UTC)
    tracker.settings[(1, "timezone")] = "Asia/Tehran"
    tracker.settings[(2, "timezone")] = "America/Los_Angeles"

    assert utils.get_user_today(make_update(user_id=1), MagicMock()) == date(2026, 9, 20)
    assert utils.get_user_today(make_update(user_id=2), MagicMock()) == date(2026, 9, 19)


# Midnight boundary, using a zone without DST so the test is stable:
# Asia/Kolkata is UTC+5:30, so local midnight is 18:30 UTC.
@pytest.mark.parametrize(
    "moment_utc, expected",
    [
        (datetime(2026, 9, 19, 18, 29, 59, tzinfo=timezone.utc), date(2026, 9, 19)),
        (datetime(2026, 9, 19, 18, 30, 0, tzinfo=timezone.utc), date(2026, 9, 20)),
    ],
    ids=["one-second-before-midnight", "exactly-midnight"],
)
def test_today_changes_exactly_at_local_midnight(
    tracker, freeze_time, moment_utc, expected
):
    freeze_time(moment_utc)
    tracker.settings[(1, "timezone")] = "Asia/Kolkata"

    assert utils.get_user_today(make_update(user_id=1), MagicMock()) == expected


def test_invalid_saved_timezone_raises(tracker):
    """
    Documents current behaviour: a corrupt timezone setting is not
    replaced by the default, it raises. (The graph handler catches it and
    shows 'I couldn't generate the graph'.)
    If you add a fallback to DEFAULT_TIMEZONE, change this test.
    """
    tracker.settings[(1, "timezone")] = "Not/AZone"

    with pytest.raises(ZoneInfoNotFoundError):
        utils.get_user_today(make_update(user_id=1), MagicMock())