import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def backup_database(db_path: str, backup_dir: str) -> str:
    db_path = os.path.abspath(db_path)
    backup_dir = os.path.abspath(backup_dir)

    if os.path.abspath(backup_dir) == os.path.abspath(db_path):
        raise ValueError("Backup directory cannot be the same as the database file path.")

    os.makedirs(backup_dir, exist_ok=True)

    if not os.path.exists(db_path):
        sqlite3.connect(db_path).close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{Path(db_path).stem}_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    if os.path.abspath(backup_path) == os.path.abspath(db_path):
        raise ValueError("Backup path cannot be the same as the database path.")

    source = sqlite3.connect(db_path)
    try:
        backup = sqlite3.connect(backup_path)
        try:
            source.backup(backup)
        finally:
            backup.close()
    finally:
        source.close()

    legacy_backup_path = os.path.join(backup_dir, os.path.basename(db_path))
    if not os.path.exists(legacy_backup_path):
        with sqlite3.connect(db_path) as source, sqlite3.connect(legacy_backup_path) as legacy:
            source.backup(legacy)

    return backup_path


def restore_database(db_path: str, backup_path: str) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    with sqlite3.connect(backup_path) as source, sqlite3.connect(db_path) as target:
        source.backup(target)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Create or restore a SQLite backup for the tracker database.")
    parser.add_argument("command", choices=["backup", "restore"], nargs="?", default="backup", help="Action to run.")
    parser.add_argument("--db-path", default=os.getenv("DATABASE_PATH", "tracker.db"), help="Path to the SQLite database file.")
    parser.add_argument("--backup-dir", default=os.getenv("BACKUP_DIR", "backups"), help="Directory where the backup file will be saved.")
    parser.add_argument("--backup-file", help="Backup file to restore from when using the restore command.")
    args = parser.parse_args(argv)

    if args.command == "backup":
        backup_path = backup_database(args.db_path, args.backup_dir)
        print(f"Backup created: {backup_path}")
        return

    if not args.backup_file:
        raise ValueError("--backup-file is required when running the restore command.")

    restore_database(args.db_path, args.backup_file)
    print(f"Database restored from: {args.backup_file}")


if __name__ == "__main__":
    main()
