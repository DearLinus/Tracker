# =========================================================
# Main menu buttons
# =========================================================

GRAPH_BUTTON = "📈 Graph"
TODAY_RECORD_BUTTON = "📝 Today Record"
NEW_RECORD_BUTTON = "➕ New Record"
STATISTICS_BUTTON = "📊 Statistics"
HISTORY_BUTTON = "📜 History"
SETTINGS_BUTTON = "⚙ Settings"
BACK_BUTTON = "⬅️ Back"
EXPORT_BUTTON = "📤 Export All History"
DELETE_DATA_BUTTON = "🗑️ Delete My Data"
RESTORE_DATA_BUTTON = "↩️ Restore My Data"
CONFIRM_YES_BUTTON = "✅ Yes"
CONFIRM_NO_BUTTON = "❌ No"

# =========================================================
# Graph timeline buttons
# =========================================================

WEEKLY_BUTTON = "Weekly"
MONTHLY_BUTTON = "Monthly"
THREE_MONTHS_BUTTON = "3 Months"
SIX_MONTHS_BUTTON = "6 Months"
ONE_YEAR_BUTTON = "1 Year"


GRAPH_TIMELINES = (
    WEEKLY_BUTTON,
    MONTHLY_BUTTON,
    THREE_MONTHS_BUTTON,
    SIX_MONTHS_BUTTON,
    ONE_YEAR_BUTTON,
)


# =========================================================
# Graph themes
# =========================================================

DARK_THEME = "dark"
LIGHT_THEME = "light"


DARK_THEME_BUTTON = "🌙 Dark Graph"
LIGHT_THEME_BUTTON = "☀️ Light Graph"


GRAPH_THEMES = (
    DARK_THEME,
    LIGHT_THEME,
)


# =========================================================
# States
# =========================================================

GRAPH_TIMELINE = "graph_timeline"
SETTINGS = "settings"
TODAY_COUNT = "today_count"
NEW_RECORD = "new_record"
CONFIRM_DELETE = "confirm_delete"


# =========================================================
# Messages
# =========================================================
INVALID_NUMBER_MESSAGE = (
    "⚠️ Please enter a whole number.\n\n"
    "Example: 8"
)

NEGATIVE_COUNT_MESSAGE = "⚠️ The count cannot be negative."
GENERIC_RECORD_ERROR_MESSAGE = (
    "⚠️ I couldn't save today's record.\n\n"
    "Please try again later."
)

WELCOME_MESSAGE = (
    "👋 Welcome to Daily Tracker!\n\n"
    "Daily Tracker is a personal tracker for "
    "recording and viewing the trend of masturbation "
    "frequency over time.\n\n"
    "You can record your daily count, review your "
    "history and statistics, and visualize your "
    "progress with a graph.\n\n"
    "Choose an option below:"
)

RECORD_SAVED_TEMPLATE = (
    "✅ Record saved successfully.\n\n"
    "Date: {date_label}\n"
    "Count: {count}"
)

TODAY_RECORD_PROMPT = (
    "📝 Today Record\n\n"
    "Today is {date_label}.\n\n"
    "How many times did you do it today?\n\n"
    "Send the number only.\n"
    "Example: 8"
)

TODAY_RECORD_UPDATE_PROMPT = (
    "📝 Today Record\n\n"
    "Today's current record is {count}.\n\n"
    "Send the new count to update it.\n\n"
    "Example: 8"
)

INVALID_DATE_MESSAGE = (
    "⚠️ Invalid date.\n\n"
    "Please use YYYY-MM-DD."
)

INVALID_FORMAT_MESSAGE = (
    "⚠️ Invalid format.\n\n"
    "Use:\n"
    "YYYY-MM-DD count\n\n"
    "Example:\n"
    "2026-09-10 8"
)

COUNT_MUST_BE_WHOLE_NUMBER_MESSAGE = "⚠️ Count must be a whole number."
PENDING_DELETION_MESSAGE = (
    "⏳ Your account is scheduled for permanent deletion.\n\n"
    "You still have 7 days to restore it.\n"
    "After that, the active database data is permanently removed and the recovery snapshot is deleted.\n"
    "Historical backups follow BACKUP_RETENTION and are not removed per user."
)
PENDING_DELETION_RESTORE_MESSAGE = (
    "✅ Your data has been restored and your account is active again."
)

# Access control
ACCESS_DENIED_MESSAGE = (
    "🚫 You are not authorized to use this bot."
)

PRIVATE_CHAT_REQUIRED_MESSAGE = (
    "⚠️ This bot only works in private chats."
)
