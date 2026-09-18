from telegram import ReplyKeyboardMarkup


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📈 Graph", "📝 Today Record"],
        ["➕ New Record", "📊 Statistics"],
        ["📜 History", "⚙️ Settings"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


GRAPH_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["Weekly", "Monthly"],
        ["3 Months", "6 Months"],
        ["1 Year"],
        ["⬅️ Back"],
    ],
    resize_keyboard=True,
)


SETTINGS_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🌙 Dark Graph", "☀️ Light Graph"],
        ["⬅️ Back"],
    ],
    resize_keyboard=True,
)


BACK_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["⬅️ Back"],
    ],
    resize_keyboard=True,
)