# Daily Tracker

A Telegram bot for tracking daily records, viewing statistics, reviewing history, and visualizing trends over time.

## Features

### 📝 Record Tracking

- Add a record for any date.
- Record today's value directly.
- Update existing records.
- Delete records through the tracking logic.
- Input validation for dates and values.

### 📊 Statistics

View:

- Number of recorded days
- Total value
- Average value
- Highest recorded value

### 📜 History

View all recorded values, sorted from the newest date to the oldest.

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

The bot uses:

```text
Europe/London
````

as its common timezone when determining the current date.

### ⚠️ Error Handling

The bot includes:

* Input validation
* User-friendly error messages
* Global Telegram error handling
* Internal exception logging

Internal errors are logged instead of exposing raw exceptions to users.

### 📋 Logging

The application provides structured logs with different levels:

* `DEBUG`
* `INFO`
* `WARNING`
* `ERROR`
* `CRITICAL`

Log levels are displayed using different terminal colors for easier monitoring.

## Tech Stack

* **Python 3.12+**
* **python-telegram-bot**
* **SQLite**
* **Matplotlib**
* **python-dotenv**

## Project Structure

```text
tracker/
│
├── bot.py
├── config.py
├── keyboards.py
├── timezone.py
├── logic.py
├── graph.py
├── database.py
│
├── handlers/
│   ├── __init__.py
│   ├── constants.py
│   ├── utils.py
│   ├── start.py
│   ├── records.py
│   ├── graph.py
│   ├── settings.py
│   ├── statistics.py
│   ├── history.py
│   ├── navigation.py
│   └── router.py
│
└── services/
    ├── __init__.py
    └── tracker_service.py
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

The database stores user-specific records and settings.

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

## Development

The Telegram implementation is maintained separately from the desktop version of Daily Tracker.

The `telegram-bot` branch contains the Telegram bot implementation, while the main branch is used for the desktop application.

## License

This project is currently unlicensed.

If you plan to distribute or reuse the project, add an appropriate license to the repository.

