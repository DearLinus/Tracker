# Daily Tracker Bot

A production-ready Telegram bot for tracking daily records with statistics, history, data export, and trend visualization. Designed for multi-user deployments with persistent state, timezone support, and comprehensive access controls.

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

### 🔐 Access Control

Optional allowlist support restricts bot access to specific Telegram user IDs.

Configure in `.env`:

```env
ALLOWED_USER_IDS=123456789,987654321
```

If set with invalid syntax or zero valid IDs, the application fails immediately with a configuration error instead of silently allowing all users. This prevents accidental access control bypass.

### ⏳ Rate Limiting

Expensive operations are rate-limited to prevent abuse:

* **Graph generation**: 5 per minute per user
* **Export**: 2 per minute per user

Uses a fixed-window rate limiter tracking requests per operation and user.

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
# Required
TELEGRAM_BOT_TOKEN=your_bot_token

# Optional: restrict access to specific Telegram user IDs (comma-separated)
# If set with invalid syntax, the bot will fail at startup
ALLOWED_USER_IDS=

# Optional: custom database file path
DATABASE_PATH=tracker.db

# Required for record-count encryption. Generate once and keep it secret.
ENCRYPTION_KEY=your_fernet_key_here

# Optional: Telegram sticker IDs for visual feedback
WELCOME_STICKER_ID=
SUCCESS_STICKER_ID=
ERROR_STICKER_ID=

# Logging is currently configured internally by the application.
# Log level customization can be added in the future.


**Security notes:**
- `TELEGRAM_BOT_TOKEN` is required and validated at startup. Missing or invalid tokens cause immediate startup failure.
- `ENCRYPTION_KEY` is required for record-count encryption. It must be persistent across restarts and deployments; if it changes or is lost, previously encrypted `records.count` values become unreadable and cannot be decrypted.
- Do not store the key in the repository, in the SQLite database, or in a version-controlled file such as `.env` that is committed to Git. Keep it in a secure secret manager, an encrypted external secret store, or a protected local environment file that is not tracked by Git.
- A database backup by itself is not enough to restore encrypted data. The same `ENCRYPTION_KEY` must be available at restore time, otherwise the backup is effectively unusable for the encrypted count values.
- If `ALLOWED_USER_IDS` is set but empty/invalid, the bot will fail fast with a configuration error.

### Generate the encryption key

```bash
python scripts/generate_encryption_key.py
```

This prints a fresh Fernet key. Copy it into `.env` as:

```env
ENCRYPTION_KEY=your_generated_key_here
```

Keep this value stable and persistent for the lifetime of the database. If the key is rotated or lost, existing encrypted record counts can no longer be decrypted, so the key should be stored separately from the SQLite backup in a secure secret store or protected local secret location.

## Deployment

### Linux (systemd)

For production Linux deployments, see [docs/systemd.md](docs/systemd.md) for a complete systemd service example with:

* Service file template
* Environment configuration
* Logging setup
* Automated restarts

### General Requirements

The project is deployment-friendly because:

* All configuration is environment-variable based
* Database file location is configurable (`DATABASE_PATH`)
* Logging behavior is centralized and production-friendly
* No hardcoded paths or secrets
* Supports running alongside other processes

### Continuous Integration

The project includes a GitHub Actions CI workflow (`.github/workflows/ci.yml`) that:

* Runs on every push and pull request
* Tests against Python 3.12
* Runs the full test suite
* Validates code with Ruff linter
* Ensures all 304 tests pass
* Checks timezone-deterministic end-to-end tests

View CI status and logs in the GitHub Actions tab.

### Container Deployment

While a Dockerfile is not included, the application can be containerized by:

1. Installing Python 3.12 and dependencies from `requirements.txt`
2. Copying the application files
3. Setting environment variables for `TELEGRAM_BOT_TOKEN` and `DATABASE_PATH`
4. Running `python bot.py`

Example minimal Dockerfile approach:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

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

Database schema changes are managed through a transactional migration system tracked in the `schema_migrations` table.

Applied migrations:

> Historical note: there is an intentional gap between `005` and `007`. The codebase never used a `006` migration, and renumbering `007` would break compatibility with existing databases that already recorded the migration name. The numbering remains intentionally monotonic for historical integrity.

| Migration | Purpose |
|-----------|---------|
| `001_init_schema` | Initialize users, records, and settings tables |
| `002_add_indexes` | Add performance indexes on (user_id, record_date) and (user_id, setting_key) |
| `003_user_states` | Add user_states table for persistent conversation state |
| `004_clean_indexes` | Remove duplicate indexes and ensure canonical naming |
| `005_consolidate_index_cleanup` | Unified index cleanup: remove duplicates, drop redundant explicit indexes when SQLite autoindexes cover them |
| `007_add_rate_limits` | Add rate_limits table for operation throttling |

Each migration is applied transactionally so failures can be rolled back without leaving a partially modified schema.

## Backup and Restore

### Creating a Backup

The project includes SQLite backup utilities in `backup.py` using SQLite's native backup mechanism.

Create a backup programmatically:

```python
from backup import backup_database

# Backup to directory with auto-generated timestamp
backup_path = backup_database('tracker.db', 'backups')
print(f"Backup saved to: {backup_path}")
```

Or via CLI:

```bash
python backup.py backup --db-path tracker.db --backup-dir backups
```

**Key benefits of native SQLite backup:**
- Safe to backup while the bot is running (no database locking)
- Preserves WAL journal state
- Atomic and consistent copy
- Includes all data and indexes

### Restoring a Backup

⚠️ **Important**: Stop the bot/service before restoring to prevent write conflicts:

```bash
systemctl stop tracker  # if using systemd
```

Then restore:

```bash
python backup.py restore --db-path tracker.db --backup-file backups/tracker-2024-01-15-120305.db
```

Or programmatically:

```python
from backup import restore_database

restore_database('tracker.db', 'backups/tracker-2024-01-15-120305.db')
```

After restoration, restart the bot:

```bash
systemctl start tracker
```

### Automated Backups

Schedule regular backups using:

* **cron** (Linux): `0 2 * * * cd /path/to/tracker && python -c "from backup import backup_database; backup_database('tracker.db', 'backups')"`
* **systemd timer** (Linux): Create a timer unit to run the backup service
* **Windows Task Scheduler**: Create a task to run the backup script

### Backup Retention

Backup files are automatically timestamped. Implement retention by:
- Removing backups older than N days: `find backups -name "*.db" -mtime +30 -delete`
- Keeping only the last N backups: Manual cleanup or script

## Architecture

The project uses a layered, event-driven architecture that cleanly separates Telegram-specific code from business logic and database persistence.

```
┌─────────────────────────┐
│   Telegram Network      │
└────────────┬────────────┘
             │
┌────────────▼────────────────────────────────┐
│   handlers/                                 │
│   ├─ Telegram updates → message parsing     │
│   ├─ State machine (router.py)              │
│   ├─ User interaction flows                 │
│   └─ Inline response generation             │
└────────────┬─────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│   services/tracker_service.py               │
│   Application-scoped tracker instance       │
│   (Stored in Application.bot_data)          │
└────────────┬─────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│   logic.py                                  │
│   ├─ Business rules                         │
│   ├─ User/record operations                 │
│   ├─ Statistics & calculations              │
│   ├─ Validation                             │
│   └─ Timezone-aware logic                   │
└────────────┬─────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│   database.py                               │
│   ├─ SQLite connection                │
│   ├─ Schema + migrations                    │
│   ├─ CRUD operations                        │
│   ├─ Transactional safety                   │
│   └─ User data isolation                    │
└────────────┬─────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│   SQLite (tracker.db or DATABASE_PATH)      │
│   WAL mode, foreign key constraints         │
└─────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**: Telegram logic is isolated from business rules and database access
2. **Testability**: Each layer can be tested independently; database operations are abstracted
3. **Type Safety**: Python 3.12+ with type hints for improved readability and maintainability
4. **Error Handling**: Graceful degradation; user-friendly error messages; detailed internal logging
5. **State Management**: Persistent conversation state allows resuming flows after restarts
6. **Scalability**: SQLite supports multi-user concurrency through isolated user data and transactional database operations
7. **Maintainability**: Clear module responsibilities; minimal coupling between layers

### Module Responsibilities


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

The project includes a comprehensive automated test suite covering all application layers.

### Test Coverage

Tests are organized by module and include:

* **Database layer**: schema creation, migrations, WAL safety, backup/restore
* **Business logic**: record operations, statistics, settings, user state, timezone handling
* **Handlers**: record entry, graph generation, export, deletion, settings, navigation
* **Integration tests**: complete flows (record creation → statistics, export → CSV)
* **End-to-end tests**: multi-step user interactions with proper timezone handling
* **Rate limiting**: window bucketing, exact boundaries, operation isolation
* **Input validation**: date parsing, Persian/Arabic numeral normalization, negative-value rejection
* **Access control**: allowlist enforcement, fail-fast validation
* **Configuration**: environment setup, TESTING mode database isolation

### Running Tests

Run the complete suite:

```bash
pytest -q
```

With coverage report:

```bash
pytest --cov=. --cov-report=term-missing
```

Run specific test file:

```bash
pytest tests/test_database.py -v
```

### Current Test Results

```
304 passed in ~5 seconds
```

All tests pass on Python 3.12+ with pytest-asyncio.

## Project Structure

```text
Tracker/
├── bot.py                       # Application entry point
├── config.py                    # Configuration loading
├── database.py                  # SQLite persistence layer + migrations
├── logic.py                     # Business logic (users, records, statistics)
├── graph.py                     # Matplotlib-based trend graphs
├── keyboards.py                 # Telegram UI button definitions
├── timezone.py                  # Timezone utilities
├── backup.py                    # SQLite backup/restore using native backup API
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development/test dependencies
├── README.md                    # This file
├── LICENSE                      # GNU GPLv3 license
│
├── docs/
│   └── systemd.md              # Production deployment with systemd
│
├── handlers/                    # Telegram-specific interaction handlers
│   ├── router.py               # Message routing and state machine
│   ├── constants.py            # UI strings and constants
│   ├── start.py                # /start command
│   ├── records.py              # Record entry flows
│   ├── statistics.py           # Statistics display
│   ├── history.py              # History view
│   ├── export.py               # CSV export
│   ├── graph.py                # Graph generation and display
│   ├── settings.py             # User settings (theme, timezone)
│   ├── navigation.py           # Menu navigation
│   ├── utils.py                # Shared handler utilities
│   └── __init__.py
│
├── services/                    # Application services
│   ├── tracker_service.py      # Tracker instance management
│   └── __init__.py
│
└── tests/                       # Comprehensive test suite (304 tests)
    ├── conftest.py             # Pytest configuration and fixtures
    ├── helpers.py              # Test utility functions
    ├── test_database.py        # Database layer, migrations
    ├── test_logic.py           # Business logic
    ├── test_bot.py             # Bot initialization
    ├── test_config.py          # Configuration validation
    ├── test_backup.py          # Backup/restore functionality
    ├── test_router.py          # Message routing
    ├── test_records_*.py       # Record entry flows
    ├── test_statistics_*.py    # Statistics calculations
    ├── test_history_*.py       # History display
    ├── test_export_*.py        # CSV export
    ├── test_graph*.py          # Graph generation
    ├── test_settings_*.py      # Settings management
    ├── test_start_*.py         # /start command
    ├── test_migration_*.py     # Migration correctness
    ├── test_rate_limit.py      # Rate limiting
    ├── test_input_parsing.py   # Input validation (Persian digits, dates)
    ├── test_keyboards.py       # UI elements
    ├── test_tracker_service.py # Service layer
    ├── test_access_control.py  # Allowlist validation
    ├── test_backup_restore.py  # Backup safety
    ├── test_state_fallthrough.py # Conversation state handling
    ├── test_e2e.py             # End-to-end user flows
    └── test_*.py               # Additional module tests
```

## Development

### Code Quality

Before submitting changes, ensure:

```bash
# Run all tests
pytest -q

# Check test coverage
pytest --cov=. --cov-report=term-missing

# Lint with Ruff
ruff check .
```

All tests must pass and new code should maintain or improve test coverage.

### Branch Structure

* `telegram-bot` — Production Telegram bot implementation (active branch)
* `main` — Desktop version (separate from Telegram implementation)

### Making Changes

1. Create a feature branch from `telegram-bot`
2. Implement changes with tests
3. Verify all tests pass (`pytest -q`)
4. Check linting passes (`ruff check .`)
5. Commit with descriptive message
6. Push and create a pull request

### Testing Guidelines

* Write tests first (TDD approach) for new features
* Maintain 100% test pass rate
* Use fixtures from `tests/conftest.py` for common setup
* Test both happy paths and error cases
* Integration tests should use real database state, not mocks

## Security and Configuration Best Practices

### Environment Variables

* **Never commit** `.env` files or bot tokens
* **Never store** credentials in code or configuration files
* **Always use** environment variables or `.env` for secrets
* **Keep** production database files outside version control

### Access Control

* Use `ALLOWED_USER_IDS` to restrict bot access to specific Telegram users
* Configuration is validated at startup (fail-fast for invalid allowlists)
* User data is isolated by Telegram user ID
* Cross-user data access is impossible through the application layer

### Data Safety

* User data is protected by SQLite foreign key constraints
* Record deletion is protected by an explicit confirmation step
* Data exports are generated on-demand without caching personal data
* Database transactions ensure atomic operations

### Backup and Restore

* Use the provided `backup.py` for database backups
* Backups use SQLite's native backup mechanism (safe during active operation)
* **Stop the bot** before restoring a backup to prevent write conflicts
* Store backups separately from the main database

### Logging

* Sensitive data (tokens, user IDs) is not logged
* Application errors are logged internally without exposing stack traces to users
* Log files use rotation to prevent unbounded growth

### Input Validation

* All user input is validated:
  - Numeric fields reject negative values
  - Dates reject unsupported formats and invalid date values
  - Persian/Arabic numerals are normalized automatically
  - Graph parameters are whitelisted

### Database

* Foreign key constraints are enforced
* UNIQUE constraints prevent duplicate records per user/date
* WAL mode provides write performance and crash recovery
* Busy timeout handles concurrent access gracefully

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).
See the [LICENSE](LICENSE) file for details.
