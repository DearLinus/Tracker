# Daily Tracker

A lightweight desktop habit and activity tracker built with **Python**, **Tkinter**, **SQLite**, and **Matplotlib**.

Daily Tracker lets you record daily counts, review your history, visualize trends, and manage your data through a simple desktop interface.

## Features

* Add daily records
* Edit existing records
* Delete records
* View complete recording history
* Track statistics such as:

  * Total
  * Average
  * Highest value
* Visualize recorded data with line graphs
* Timeline filters:

  * Weekly
  * Monthly
  * 3 Months
  * 6 Months
  * 1 Year
* Interactive graph hover information
* Light, Dark, and System themes
* Persistent local settings
* SQLite-based local data storage
* Automatic update checking
* Automatic application updates
* SHA-256 update verification
* Automatic backup of user data during updates
* Rollback support if an update replacement fails

## Screenshots

Screenshots will be added here in a future release.

## Tech Stack

* **Python**
* **Tkinter** — graphical user interface
* **SQLite** — local database
* **Matplotlib** — data visualization
* **Git / GitHub** — version control and releases

## Project Structure

```text
tracker/
├── main.py
├── gui.py
├── logic.py
├── database.py
├── updater.py
├── version.py
├── .gitignore
├── tracker.db
└── tracker_settings.json
```

### Architecture

The application follows a simple layered architecture:

```text
GUI
 ↓
Logic
 ↓
Database
```

### `main.py`

Application entry point.

### `gui.py`

Contains the graphical user interface and user interaction logic.

### `logic.py`

Contains the application's business logic and validation.

### `database.py`

Handles SQLite database operations.

### `updater.py`

Runs the update process separately from the main application.

It downloads the new release, verifies its SHA-256 hash, preserves user data, replaces application files, and launches the updated application.

### `version.py`

Stores the current application version.

## Data Storage

Daily Tracker uses SQLite for persistent record storage.

The database contains records in the following form:

```text
record_date → count
```

Each date can have one recorded value.

User-specific files such as:

```text
tracker.db
tracker_settings.json
update_backups/
```

are intentionally excluded from Git through `.gitignore`.

This means users keep their own data independently from the application source code.

## Running From Source

### Requirements

* Python 3
* Tkinter
* Matplotlib

Clone the repository:

```bash
git clone https://github.com/DearLinus/Tracker.git
cd Tracker
```

Install the Python dependency:

```bash
pip install matplotlib
```

Run the application:

```bash
python main.py
```

## Releases

Stable application versions are distributed through GitHub Releases.

Release archives follow this naming convention:

```text
DailyTracker-vX.Y.Z.zip
```

For example:

```text
DailyTracker-v1.1.0.zip
```

Release archives are not stored directly in the Git repository.

## Automatic Updates

Daily Tracker includes an automatic update system.

The update process works approximately as follows:

```text
Check for Updates
        ↓
GitHub Releases API
        ↓
Compare Versions
        ↓
New Version Available?
        ↓
Download Release ZIP
        ↓
Verify SHA-256
        ↓
Close Application
        ↓
Run updater.py
        ↓
Backup User Data
        ↓
Replace Application Files
        ↓
Launch New Version
```

The updater is a separate process because the running application should not attempt to replace its own files.

User data is preserved during updates.

## Versioning

The project uses semantic-style version numbers:

```text
MAJOR.MINOR.PATCH
```

For example:

```text
1.1.0
```

The current application version is defined in `version.py`.

## Development

The project is currently under active development.

Planned improvements include:

* Windows executable packaging
* Linux AppImage packaging
* More comprehensive error handling
* Automated testing
* Improved release automation
* Additional data visualization features

## License

License information will be added in a future release.
