# Daily Tracker

A Telegram bot for tracking daily records, viewing statistics, reviewing history, and visualizing trends over time.

## Features

### 📝 Record Tracking

- Add a record for any date.
- Record today's value directly.
- Update existing records.
- Input validation for dates and values.

> **Note:** Delete functionality will be added in future updates.

### 📊 Statistics

View:

- Number of recorded days
- Total value
- Average value
- Highest recorded value

### 📜 History

Review recent activity for the last 7 days, including days with saved records. Empty days are displayed as `No record` instead of `0` to make missing data explicit.

### 📈 Graphs

Generate trend graphs for:

- Weekly
- Monthly
- 3 Months
- 6 Months
- 1 Year

The graph also includes a guide for today's recorded value when available.

### 🎨 Graph Themes

Choose between:

- 🌙 Dark
- ☀️ Light

The selected theme is stored separately for each user.

### 👤 Multi-user Support

The bot supports multiple Telegram users.

Each user's:

- Records
- Settings
- Statistics

are kept separate using their Telegram user ID.

### 🌍 Timezone

The bot currently defaults to:

```text
Asia/Tehran
```

for the current-date calculation. Users can also keep their own timezone override in settings, and the project is structured so more timezone-aware behavior can be added without changing the whole app.

### ⚠️ Error Handling

The bot includes:

* Input validation
* User-friendly error messages
* Global Telegram error handling
* Internal exception logging
* Safe environment-based secret loading via `.env`

Internal errors are logged instead of exposing raw exceptions to users.

### 📋 Logging

The application provides structured logs with different levels:

* `DEBUG`
* `INFO`
* `WARNING`
* `ERROR`
* `CRITICAL`

Log levels are displayed using different terminal colors for easier monitoring.

Logs are automatically rotated to prevent unbounded log file growth (max 10MB per file, up to 5 backups).

### 💾 Conversation State Persistence

User's conversation state (awaiting input for specific flows) is persisted in the database, allowing the bot to recover conversational context even after restarts.

## Tech Stack

* **Python 3.12+**
* **python-telegram-bot**
* **SQLite**
* **Matplotlib**
* **python-dotenv**

### Platform-Specific Requirements

#### Linux/macOS
No additional system packages required beyond Python 3.12+.

#### Windows
You may need to install additional dependencies for Matplotlib rendering:

```powershell
# If you encounter issues with Matplotlib graph generation:
pip install pywin32
python -m pip install --upgrade pillow
```

The `pywin32` package is typically needed if Matplotlib fails to initialize the display backend on Windows.

## Project Structure

```text
tracker/
│
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
│
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
│
├── services/
│   ├── __init__.py
│   └── tracker_service.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_database.py
    ├── test_export_handler.py
    ├── test_graph.py
    ├── test_graph_handler.py
    ├── test_history_handler.py
    ├── test_keyboards.py
    ├── test_logic.py
    ├── test_records_handler.py
    ├── test_records_integration.py
    ├── test_router.py
    ├── test_settings_handler.py
    ├── test_start_handler.py
    ├── test_statistics_handler.py
    └── test_utils.py
```

## Architecture

The project is divided into several components.

### `bot.py`

Application entry point.

Responsible for:

* Creating the Telegram application
* Registering handlers
* Configuring logging
* Handling global errors
* Starting polling

### `handlers/`

Contains Telegram-specific handlers.

Each feature is separated into its own module:

* `start.py` — `/start` command
* `records.py` — creating and updating records
* `graph.py` — graph menu and graph delivery
* `settings.py` — user settings
* `statistics.py` — statistics
* `history.py` — history
* `navigation.py` — navigation
* `router.py` — text message routing
* `utils.py` — shared handler utilities
* `constants.py` — shared constants

### `logic.py`

Contains the application's core tracking logic.

It handles:

* User creation
* Record creation
* Record updates
* Record deletion
* Record retrieval
* Statistics
* User settings
* Input validation

### `database.py`

Handles SQLite database operations.

The database stores user-specific records, settings, and conversation state using a migration-aware schema and transactional commits/rollbacks.

Features:
* Atomic migrations (executed statement-by-statement for safe rollback)
* User state persistence (remembers conversation state across restarts)
* Foreign key constraints and cascading deletes

### `backup.py`

Provides backup and restore helpers built on SQLite's native `backup()` API so database copies remain consistent while the database is in use.

### `graph.py`

Responsible for generating trend graphs using Matplotlib.

It receives the user's records and graph settings and produces the requested graph.

### `services/tracker_service.py`

Provides the shared `TrackerLogic` instance used by the Telegram handlers.

### `timezone.py`

Provides the application's common timezone and current-date calculation.

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

