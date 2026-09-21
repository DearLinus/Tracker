# Daily Tracker

A Telegram bot for tracking daily counts, viewing statistics, checking history, and generating trend graphs over time.

## Features

### 📝 Record Tracking

- Add a record for today.
- Add a record for any past date.
- Update an existing record.
- Validate user input for numeric values and date format.

> Delete functionality is not implemented yet and will be added in a future update.

### 📊 Statistics

The bot can show:

- Number of recorded days
- Total value
- Average value
- Highest recorded value

### 📜 History

Review the last 7 days with explicit `No record` markers for missing dates instead of silently treating them as zero.

### 📈 Graphs

Generate charts for:

- Weekly
- Monthly
- 3 Months
- 6 Months
- 1 Year

The graph also includes a visual guide for the current day's value when available.

### 🎨 Theme Support

Each user can choose a graph theme:

- Dark
- Light

The selected theme is stored per Telegram user.

### 👤 Multi-user Support

The bot keeps each user's:

- records
- settings
- statistics
- conversation state

separate using their Telegram user ID.

### 🌍 Timezone-aware Date Logic

The app uses a default timezone of:

```text
Asia/Tehran
```

Users can override it in settings. Date calculations are based on the user's local timezone so the "today" value is correct for each user.

### ⚠️ Validation and Error Handling

The bot includes:

- input validation for numeric and date values
- friendly user-facing error messages
- Telegram global error handling
- internal logging without exposing stack traces to users
- fail-fast configuration for required secrets

### 📋 Logging

The application logs at multiple levels:

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

Logs are rotated automatically to prevent the log file from growing without limit.

### 💾 Conversation State Persistence

User flow state is persisted in SQLite and restored after a restart, so a bot restart does not lose the user's current step in a conversation flow.

## Requirements

- Python 3.12+
- SQLite
- python-telegram-bot
- Matplotlib
- python-dotenv

## Setup

1. Clone the repository.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with at least:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

Optional values:

```env
DATABASE_PATH=tracker.db
WELCOME_STICKER_ID=your_welcome_sticker_id
SUCCESS_STICKER_ID=your_success_sticker_id
ERROR_STICKER_ID=your_error_sticker_id
```

If `TELEGRAM_BOT_TOKEN` is missing, the application exits immediately with a clear error instead of continuing with an invalid token.

## Windows Notes

On Windows, if Matplotlib has trouble initializing or rendering graphs, install the additional packages below:

```powershell
pip install pywin32 pillow
```

The project also includes `tzdata` in `requirements.txt` for Windows environments, which helps with timezone resolution.

## Project Structure

```text
tracker/
├── backup.py
├── bot.py
├── config.py
├── database.py
├── graph.py
├── keyboards.py
├── logic.py
├── README.md
├── requirements.txt
├── timezone.py
├── version.py
├── handlers/
│   ├── __init__.py
│   ├── constants.py
│   ├── export.py
│   ├── graph.py
│   ├── history.py
│   ├── navigation.py
│   ├── records.py
│   ├── router.py
│   ├── settings.py
│   ├── start.py
│   ├── statistics.py
│   └── utils.py
├── services/
│   ├── __init__.py
│   └── tracker_service.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_export_handler.py
│   ├── test_graph.py
│   ├── test_graph_handler.py
│   ├── test_history_handler.py
│   ├── test_keyboards.py
│   ├── test_logic.py
│   ├── test_records_handler.py
│   ├── test_records_integration.py
│   ├── test_router.py
│   ├── test_settings_handler.py
│   ├── test_start_handler.py
│   ├── test_statistics_handler.py
│   └── test_utils.py
└── .env
```

## Architecture

The project is split into layered components:

### `bot.py`

Main entry point. Responsible for:

- creating the Telegram application
- registering handlers
- configuring logging
- starting the polling loop
- attaching the application-scoped tracker instance

### `handlers/`

Telegram-specific logic for commands and menu flows:

- `start.py` — `/start`
- `records.py` — create/update daily records
- `graph.py` — graph menu and graph creation
- `settings.py` — user settings
- `statistics.py` — statistics screen
- `history.py` — recent activity
- `navigation.py` — menu navigation
- `router.py` — dispatching incoming text
- `utils.py` — shared helper logic
- `constants.py` — shared route and UI constants

### `logic.py`

Core business logic for:

- user creation
- record saving and updates
- record retrieval
- statistics
- settings
- validation rules

### `database.py`

SQLite access layer with transactional migrations and schema management.

Key points:

- migration support with transactional execution
- foreign keys and integrity checks
- per-user settings and persisted state
- WAL mode and busy timeout configuration

### `backup.py`

SQLite backup utilities for safely copying DB state while the bot is running.

### `graph.py`

Generates chart images using Matplotlib, with sizing and rendering logic tuned for Telegram-friendly output.

### `services/tracker_service.py`

Creates and stores the `TrackerLogic` instance on the Telegram `Application` object as `bot_data["tracker"]`.

Handlers obtain the tracker with `get_tracker_from_context(context)` instead of relying on a process-wide singleton.

### `timezone.py`

Contains common timezone helper logic and current-date calculations.

## Notes

- The project currently focuses on creating and updating records rather than deletion.
- The bot reads and restores persisted user state after a restart.
- The tracker is application-scoped, which makes tests and runtime state easier to reason about.
- The Telegram token is required and validated early so misconfiguration fails fast.

## Configuration

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_bot_token

WELCOME_STICKER_ID=
SUCCESS_STICKER_ID=
ERROR_STICKER_ID=
```

The sticker IDs are optional.

Do not commit your `.env` file or bot token to the repository.

## Installation

Clone the repository:

```bash
git clone https://github.com/DearLinus/Tracker.git
cd Tracker
```

Switch to the Telegram bot branch:

```bash
git checkout telegram-bot
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it on Linux/macOS:

```bash
source venv/bin/activate
```

On Windows:

```powershell
venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create your `.env` file and configure the Telegram bot token.

## Running the Bot

Run:

```bash
python bot.py
```

The bot will start polling Telegram for updates.

## Main Menu

After starting the bot with `/start`, the main menu provides:

```text
📈 Graph
📝 Today Record
➕ New Record
📊 Statistics
📜 History
⚙️ Settings
```

## Database

The Telegram bot uses SQLite for persistent storage.

Records and settings are associated with each Telegram user's ID, allowing multiple users to use the same bot independently.

A small backup flow is already supported through the helper functions in `backup.py`.

### Backup helper

You can create a SQLite-safe backup like this:

```bash
python -c "from backup import backup_database; print(backup_database('tracker.db', 'backups'))"
```

This creates a timestamped backup in the `backups/` folder using SQLite's native backup mechanism.

For a simple scheduled flow, you can run the same command from a cron job or systemd timer, for example every night at 02:00.

## Development

The Telegram implementation is maintained separately from the desktop version of Daily Tracker.

The `telegram-bot` branch contains the Telegram bot implementation, while the main branch is used for the desktop application.

## License

This project is currently unlicensed.

If you plan to distribute or reuse the project, add an appropriate license to the repository.

