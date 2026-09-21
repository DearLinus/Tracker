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
        raise FileNotFoundError(f"Source database not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{Path(db_path).stem}_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    if os.path.abspath(backup_path) == os.path.abspath(db_path):
        raise ValueError("Backup path cannot be the same as the database path.")

    # Use context managers to ensure connections are closed promptly.
    with sqlite3.connect(db_path) as source, sqlite3.connect(backup_path) as backup:
        source.backup(backup)

    # Rotation / retention: remove older timestamped backups beyond retention count
    retention = int(os.getenv("BACKUP_RETENTION", "7"))

    # Use a strict naming convention to identify timestamped backups created
    # by this tool: <stem>_YYYYMMDD_HHMMSS*.db. This avoids accidentally
    # matching unrelated files that merely share a prefix.
    import re

    stem = Path(db_path).stem
    pattern = re.compile(rf"^{re.escape(stem)}_\d{{8}}_\d{{6}}.*\.db$")

    timestamped_backups = sorted(
        [p for p in Path(backup_dir).iterdir() if p.is_file() and pattern.match(p.name)],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old in timestamped_backups[retention:]:
        try:
            old.unlink()
        except Exception:
            # Do not fail the backup if cleanup cannot remove an old file
            pass

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
