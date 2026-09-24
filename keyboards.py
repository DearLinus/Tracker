from telegram import ReplyKeyboardMarkup

from handlers.constants import (
    BACK_BUTTON,
    CONFIRM_NO_BUTTON,
    CONFIRM_YES_BUTTON,
    DARK_THEME_BUTTON,
    DELETE_DATA_BUTTON,
    EXPORT_BUTTON,
    GRAPH_BUTTON,
    HISTORY_BUTTON,
    LIGHT_THEME_BUTTON,
    MONTHLY_BUTTON,
    NEW_RECORD_BUTTON,
    ONE_YEAR_BUTTON,
    RESTORE_DATA_BUTTON,
    SETTINGS_BUTTON,
    SIX_MONTHS_BUTTON,
    STATISTICS_BUTTON,
    THREE_MONTHS_BUTTON,
    TODAY_RECORD_BUTTON,
    WEEKLY_BUTTON,
)

# =========================================================
# Main keyboard
# =========================================================

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            GRAPH_BUTTON,
            TODAY_RECORD_BUTTON,
        ],
        [
            NEW_RECORD_BUTTON,
            STATISTICS_BUTTON,
        ],
        [
            HISTORY_BUTTON,
            SETTINGS_BUTTON,
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# History keyboard
# =========================================================

HISTORY_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            EXPORT_BUTTON,
        ],
        [
            BACK_BUTTON,
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# Graph keyboard
# =========================================================

GRAPH_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            WEEKLY_BUTTON,
            MONTHLY_BUTTON,
        ],
        [
            THREE_MONTHS_BUTTON,
            SIX_MONTHS_BUTTON,
        ],
        [
            ONE_YEAR_BUTTON,
        ],
        [
            BACK_BUTTON,
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# Settings keyboard
# =========================================================

SETTINGS_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            DARK_THEME_BUTTON,
            LIGHT_THEME_BUTTON,
        ],
        [
            DELETE_DATA_BUTTON,
        ],
        [
            BACK_BUTTON,
        ],
    ],
    resize_keyboard=True,
)

PENDING_DELETE_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            RESTORE_DATA_BUTTON,
        ],
        [
            BACK_BUTTON,
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# Confirm delete keyboard
# =========================================================

CONFIRM_DELETE_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            CONFIRM_YES_BUTTON,
            CONFIRM_NO_BUTTON,
        ],
        [
            BACK_BUTTON,
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# Back keyboard
# =========================================================

BACK_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            BACK_BUTTON,
        ],
    ],
    resize_keyboard=True,
)