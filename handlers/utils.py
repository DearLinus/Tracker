from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from services.tracker_service import get_tracker_from_context as get_tracker
import os
from typing import Set


from timezone import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)

def get_user_id(update: Update):
    return update.effective_user.id


def reset_state(context: ContextTypes.DEFAULT_TYPE):
    """Clear ephemeral in-memory state only (keeps tests backwards-compatible)."""
    context.user_data.pop("awaiting", None)


def set_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: str):
    """Set both in-memory and persistent state for the user."""
    context.user_data["awaiting"] = state
    user_id = get_user_id(update)
    get_tracker(context).set_user_state(user_id, "awaiting", state)


def get_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read state: prefer in-memory (current request), fall back to persisted."""
    if "awaiting" in context.user_data:
        return context.user_data["awaiting"]
    user_id = get_user_id(update)
    state = get_tracker(context).get_user_state(user_id, "awaiting")
    if state is not None:
        # mirror into context for faster subsequent access
        context.user_data["awaiting"] = state
    return state


def clear_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear both in-memory and persisted state when update is available."""
    context.user_data.pop("awaiting", None)
    user_id = get_user_id(update)
    get_tracker(context).delete_user_state(user_id, "awaiting")


async def send_sticker_if_available(update: Update, sticker_id: str | None):
    """Send a sticker if available. Telegram errors are logged and not propagated.
    
    Sticker failures must never break the main handler flow (e.g., blocking a record save).
    """
    if not sticker_id:
        return
    try:
        await update.message.reply_sticker(sticker_id)
    except TelegramError as exc:
        logger.warning("Failed to send sticker: %s", exc)


def get_graph_theme(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)

    return get_tracker(context).get_setting(
        user_id,
        "graph_theme",
        default="dark",
    )



def get_user_timezone(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)

    return get_tracker(context).get_setting(
        user_id,
        "timezone",
        DEFAULT_TIMEZONE,
    )



def get_user_today(update, context: ContextTypes.DEFAULT_TYPE):
    timezone = get_user_timezone(update, context)

    return datetime.now(
        ZoneInfo(timezone)
    ).date()


def parse_int(text: str) -> int:
    """
    Parse an integer from text accepting ASCII digits and Arabic-Indic / Eastern Arabic-Indic.
    Preserves support for localized digits used by some users.

    Rejects non-integer formats such as '1_0' or floats '3.5'. Allows leading '+' like '+5'.
    """
    if not isinstance(text, str):
        raise ValueError("invalid literal for int()")

    s = text.strip()

    # allow leading plus or minus; caller can validate negativity
    if s.startswith("+"):
        s = s[1:]
    elif s.startswith("-"):
        # keep the leading '-' so int() can parse a negative number
        pass

    # Normalize Arabic-Indic digits to ASCII
    arabic_map = {
        ord("٠"): "0",
        ord("١"): "1",
        ord("٢"): "2",
        ord("٣"): "3",
        ord("٤"): "4",
        ord("٥"): "5",
        ord("٦"): "6",
        ord("٧"): "7",
        ord("٨"): "8",
        ord("٩"): "9",
        ord("۰"): "0",
        ord("۱"): "1",
        ord("۲"): "2",
        ord("۳"): "3",
        ord("۴"): "4",
        ord("۵"): "5",
        ord("۶"): "6",
        ord("۷"): "7",
        ord("۸"): "8",
        ord("۹"): "9",
    }

    normalized = s.translate(arabic_map)

    # reject underscores or decimal points
    if "_" in normalized or "." in normalized or "," in normalized:
        raise ValueError("invalid literal for int()")

    # Now rely on int() which will raise ValueError for bad formats
    try:
        return int(normalized)
    except ValueError:
        raise


_CACHED_ALLOWED_IDS: set | None = None
_CACHED_ALLOWED_RAW: str | None = None


def _parse_allowed_user_ids() -> Set[int]:
    """Parse ALLOWED_USER_IDS env var into a set of ints.

    Format: comma-separated integers, e.g. "123,456".
    Empty or missing value returns an empty set meaning "no restriction".
    Malformed entries are ignored.
    """
    global _CACHED_ALLOWED_IDS, _CACHED_ALLOWED_RAW
    raw = os.getenv("ALLOWED_USER_IDS", "").strip()

    # If cached and the raw env matches previous value, return cached set
    if _CACHED_ALLOWED_RAW is not None and raw == _CACHED_ALLOWED_RAW and _CACHED_ALLOWED_IDS is not None:
        return set(_CACHED_ALLOWED_IDS)

    if not raw:
        _CACHED_ALLOWED_IDS = set()
        _CACHED_ALLOWED_RAW = raw
        return set()

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    ids: Set[int] = set()
    for p in parts:
        try:
            ids.add(int(p))
        except ValueError:
            # Ignore malformed entries
            continue
    _CACHED_ALLOWED_IDS = set(ids)
    _CACHED_ALLOWED_RAW = raw
    return set(ids)


def is_user_allowed(user_id: int) -> bool:
    """Return True if the user_id is allowed to use the bot.

    If `ALLOWED_USER_IDS` is not set or empty, all users are allowed.
    """
    allowed = _parse_allowed_user_ids()
    if not allowed:
        return True
    return user_id in allowed


def is_private_chat(update) -> bool:
    """Return True if the incoming update is from a private chat (one-to-one).

    Works with `Update` objects or any object exposing `message.chat.type`.
    """
    try:
        chat_type = update.message.chat.type
    except Exception:
        # Keep backwards compatibility with tests that don't model chat.type:
        # if chat.type is missing, assume private.
        return True

    return chat_type == "private"