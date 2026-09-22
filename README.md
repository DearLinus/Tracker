# Daily Tracker

A Telegram bot for tracking daily records, viewing statistics and history, exporting data, and generating trend graphs over time.

## Features

### 📝 Record Tracking

* Add a record for today.
* Add a record for any past date.
* Update an existing record.
* Validate numeric input and date formats.
* Prevent negative values.
* Prevent records from being created for future dates.
* Store records separately for each Telegram user.

### 📊 Statistics

The bot provides:

* Number of recorded days
* Total recorded value
* Average value
* Highest recorded value

### 📜 History

Review recent activity with explicit `No record` markers for missing dates instead of silently treating missing records as zero.

### 📤 Data Export

Users can export their complete recorded history as a CSV file directly from the bot.

### 🗑️ Delete My Data

Users can permanently delete their own data through the Settings menu.

Deletion requires an explicit confirmation step before it is performed.

User-related records, settings, and persisted conversation state are linked through SQLite foreign keys and are deleted together.

### 📈 Graphs

Generate trend graphs for:

* Weekly
* Monthly
* 3 Months
* 6 Months
* 1 Year

Graphs include the most recently recorded value within the selected time range when a record is available.

### 🎨 Graph Themes

Each user can choose between:

* Dark
* Light

The selected graph theme is stored separately for each Telegram user.

### 👤 Multi-user Support

The bot is designed for multiple Telegram users.

Each user's:

* records
* settings
* statistics
* conversation state

are isolated using their Telegram user ID.

One user's data cannot be accessed through another user's tracker records.

### 🌍 Timezone-aware Date Logic

Date calculations are timezone-aware.

The default timezone is:

```text
Asia/Tehran
```

The application can resolve a user's stored timezone when calculating dates such as "today". However, there is currently no user-facing timezone selector in the Telegram settings menu.

User-configurable timezone selection can be added as a future feature.

### 💾 Persistent Conversation State

Conversation state is persisted in SQLite.

This allows the bot to restore the user's current flow after a restart instead of losing the state immediately when the process stops.

Examples include:

* entering a new record
* selecting a graph timeline
* confirming data deletion
* navigating settings

### ⚠️ Validation and Error Handling

The bot includes:

* numeric input validation
* date validation
* negative-value validation
* future-date validation
* graph option validation
* friendly user-facing error messages
* global Telegram error handling
* internal exception logging
* fail-fast configuration for required secrets

Unexpected internal errors are logged without exposing stack traces to users.

### 📋 Logging

The application supports multiple logging levels:

* DEBUG
* INFO
* WARNING
* ERROR
* CRITICAL

Log files use rotation to prevent them from growing indefinitely.

## Requirements

* Python 3.12+
* SQLite
* python-telegram-bot
* Matplotlib
* python-dotenv
* pytest and pytest-asyncio for development/testing

The project pins its Python package dependencies in `requirements.txt`.

Development/test dependencies are provided in `requirements-dev.txt`.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/DearLinus/Tracker.git
cd Tracker
```

### 2. Switch to the Telegram bot branch

```bash
git checkout telegram-bot
```

### 3. Create a virtual environment

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

### 4. Install dependencies

For normal runtime:

```bash
pip install -r requirements.txt
```

For development and testing:

```bash
pip install -r requirements-dev.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
```

Optional settings:

```env
DATABASE_PATH=tracker.db

WELCOME_STICKER_ID=
SUCCESS_STICKER_ID=
ERROR_STICKER_ID=
```

`TELEGRAM_BOT_TOKEN` is required. If it is missing, the application fails immediately with a configuration error instead of starting with an invalid configuration.

Do not commit `.env` or your bot token to the repository.

## Deployment

For production Linux deployments, see [docs/systemd.md](docs/systemd.md) for a systemd service example.

The project is already close to container-friendly deployment because it reads most configuration from environment variables, supports a configurable SQLite path via `DATABASE_PATH`, and keeps runtime artifacts in clearly defined directories.

## Windows Notes

The project includes `tzdata` for Windows environments to support timezone resolution.

If Matplotlib has environment-specific rendering issues on Windows, the following packages may also be useful:

```powershell
pip install pywin32 pillow
```

## Running the Bot

Start the bot with:

```bash
python bot.py
```

The bot starts polling Telegram for updates.

After sending `/start`, the main menu provides:

```text
📈 Graph
📝 Today Record
➕ New Record
📊 Statistics
📜 History
⚙ Settings
```

Additional actions such as exporting history and deleting personal data are available through the relevant menus.

## Database

The Telegram bot uses SQLite for persistent storage.

The database contains separate data for each Telegram user, including:

* user information
* daily records
* settings
* persisted conversation state

### Database integrity

The database layer uses:

* foreign keys
* unique constraints
* validation constraints
* transactions
* WAL journal mode
* a busy timeout for concurrent access

Records are uniquely associated with a user and date.

### Database migrations

Database schema changes are handled through a migration system tracked in the `schema_migrations` table.

Current migrations include:

```text
001_init_schema
002_add_indexes
003_user_states
004_clean_indexes
```

Each migration is applied transactionally so that a failed migration can be rolled back instead of leaving a partially modified schema.

## Backup

The project includes SQLite backup utilities in `backup.py`.

A backup can be created with:

```bash
python -c "from backup import backup_database; print(backup_database('tracker.db', 'backups'))"
```

The backup uses SQLite's native backup mechanism, allowing the database to be backed up safely while the bot is running.

The resulting backup is timestamped and stored in the specified directory.

For automated backups, the command can be scheduled with tools such as:

* cron
* systemd timers
* Windows Task Scheduler

## Architecture

The project uses a layered architecture that separates Telegram-specific code from business logic and database access.

```text
Telegram
   │
   ▼
handlers/
   │
   ▼
services/tracker_service.py
   │
   ▼
logic.py
   │
   ▼
database.py
   │
   ▼
SQLite
```

### `bot.py`

Main application entry point.

Responsible for:

* creating the Telegram application
* registering handlers
* configuring logging
* creating the application-scoped tracker
* attaching the tracker to `Application.bot_data`
* starting the polling loop
* registering global error handling

### `handlers/`

Contains Telegram-specific interaction logic.

```text
handlers/
├── constants.py
├── export.py
├── graph.py
├── history.py
├── navigation.py
├── records.py
├── router.py
├── settings.py
├── start.py
├── statistics.py
└── utils.py
```

Responsibilities include:

* `/start`
* record creation and updates
* graph generation
* graph theme settings
* statistics
* history
* CSV export
* data deletion and confirmation
* menu navigation
* routing incoming messages
* shared Telegram helper functions

### `services/tracker_service.py`

Provides access to the application's `TrackerLogic` instance.

The tracker is stored on the Telegram `Application` object:

```python
application.bot_data["tracker"]
```

Handlers retrieve it through:

```python
get_tracker_from_context(context)
```

This avoids relying on a process-wide singleton and makes application state easier to test and manage.

### `logic.py`

Contains the core business logic, including:

* user creation
* record creation and updates
* record retrieval
* statistics
* settings
* persisted user state
* validation
* timezone-aware date handling
* user data deletion

The logic layer is independent of Telegram-specific message handling.

### `database.py`

Provides the SQLite persistence layer.

Responsibilities include:

* database connections
* schema creation
* transactional migrations
* CRUD operations
* foreign-key enforcement
* user data isolation
* settings persistence
* conversation state persistence
* SQLite performance configuration

### `backup.py`

Provides SQLite backup functionality using SQLite's native backup mechanism.

### `graph.py`

Generates graph images using Matplotlib.

It handles:

* timeline filtering
* missing records
* graph themes
* graph sizing
* recent-value guides
* Telegram-friendly image output

### `timezone.py`

Contains shared timezone-related helpers and the default timezone configuration.

## Testing

The project has an automated test suite covering the main application layers.

Tests include:

* database behavior
* migrations
* business logic
* graph generation
* graph handlers
* record handlers
* integration flows
* end-to-end flows
* router behavior
* settings
* statistics
* history
* CSV export
* keyboards
* configuration
* tracker service
* timezone-related utilities
* backup functionality
* bot setup

Run the complete test suite with:

```bash
pytest -q
```

Current test result:

```text
211 passed
```

The full suite currently completes successfully.

## Project Structure

```text
Tracker/
├── backup.py
├── bot.py
├── config.py
├── database.py
├── graph.py
├── keyboards.py
├── logic.py
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── timezone.py
├
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
    ├── test_backup.py
    ├── test_bot.py
    ├── test_config.py
    ├── test_database.py
    ├── test_e2e.py
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
    ├── test_tracker_service.py
    └── test_utils.py
```

## Development

The Telegram bot is maintained separately from the desktop version of Daily Tracker.

The `telegram-bot` branch contains the Telegram implementation, while the main branch is used for the desktop application.

Before submitting changes, run:

```bash
pytest -q
```

All tests should pass before committing changes.

## Security and Configuration Notes

* Never commit `.env`.
* Never commit the Telegram bot token.
* Keep production database files outside version control.
* Use backups for important production databases.
* User data is isolated by Telegram user ID.
* Data deletion is protected by an explicit confirmation step.

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).
See the [LICENSE](LICENSE) file for details.
