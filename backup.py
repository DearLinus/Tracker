"""Database backup/restore helpers.

Important: a backup is only useful if the matching ENCRYPTION_KEY is backed up
separately as well. Otherwise the restored database cannot decrypt record counts.
"""

import argparse
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _prune_old_files(directory: str, pattern: str, retention: int) -> None:
    """Remove older files with the given timestamped naming pattern beyond the retention count."""
    try:
        matches = sorted(
            [p for p in Path(directory).iterdir() if p.is_file() and re.fullmatch(pattern, p.name)],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return

    for old in matches[retention:]:
        try:
            old.unlink()
        except OSError:
            logger.warning("Failed to remove old file %s", old)


def backup_database(db_path: str, backup_dir: str) -> str:
    db_path = os.path.abspath(db_path)
    backup_dir = os.path.abspath(backup_dir)

    if os.path.abspath(backup_dir) == os.path.abspath(db_path):
        raise ValueError("Backup directory cannot be the same as the database file path.")

    os.makedirs(backup_dir, exist_ok=True)

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Source database not found: {db_path}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"{Path(db_path).stem}_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    if os.path.abspath(backup_path) == os.path.abspath(db_path):
        raise ValueError("Backup path cannot be the same as the database path.")

    print(
        "WARNING: keep ENCRYPTION_KEY backed up separately; otherwise this database backup cannot decrypt record counts.",
        file=sys.stderr,
    )

    # Use context managers to ensure connections are closed promptly.
    with sqlite3.connect(db_path) as source, sqlite3.connect(backup_path) as backup:
        source.backup(backup)

    # Rotation / retention: remove older timestamped backups beyond retention count
    retention = max(0, int(os.getenv("BACKUP_RETENTION", "7")))

    # Use a strict naming convention to identify timestamped backups created
    # by this tool: <stem>_YYYYMMDD_HHMMSS*.db. This avoids accidentally
    # matching unrelated files that merely share a prefix.
    import re

    stem = Path(db_path).stem
    pattern = rf"^{re.escape(stem)}_\d{{8}}_\d{{6}}.*\.db$"
    _prune_old_files(backup_dir, pattern, retention)

    return backup_path


def restore_database(db_path: str, backup_path: str) -> None:
    # Ensure backup file exists before doing anything that could create DB file
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # Validate the backup by opening it read-only and running PRAGMA integrity_check
    uri = f"file:{os.path.abspath(backup_path)}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as src_ro:
            cur = src_ro.execute("PRAGMA integrity_check;")
            row = cur.fetchone()
            if row is None or row[0] != "ok":
                raise ValueError("Backup integrity check failed")
    except sqlite3.DatabaseError as exc:
        # Not a valid SQLite database
        raise ValueError("Backup file is not a valid SQLite database") from exc

    # Ensure target directory exists but DO NOT open the target DB yet (to avoid
    # creating an empty DB file in case of validation failures).
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    # If the target DB exists, create a safety copy before overwriting it.
    # Use SQLite's backup API instead of a raw file copy so committed WAL data
    # is also captured in the safety copy.
    if os.path.exists(db_path):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safety_path = f"{db_path}.pre_restore_{timestamp}.db"
        with sqlite3.connect(db_path) as source, sqlite3.connect(safety_path) as target:
            source.backup(target)

        retention = max(0, int(os.getenv("BACKUP_RETENTION", "7")))
        target_name = Path(db_path).name
        pattern = rf"^{re.escape(target_name)}\.pre_restore_\d{{8}}_\d{{6}}.*\.db$"
        _prune_old_files(os.path.dirname(db_path) or ".", pattern, retention)

    # Now perform the actual restore using SQLite's backup API. Open the
    # source in read-only mode and the target normally (writable). Using the
    # context managers ensures connections are closed properly.
    src_uri = f"file:{os.path.abspath(backup_path)}?mode=ro"
    with sqlite3.connect(src_uri, uri=True) as source, sqlite3.connect(db_path) as target:
        source.backup(target)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Create or restore a SQLite backup for the tracker database.")
    parser.add_argument("command", choices=["backup", "restore"], nargs="?", default="backup", help="Action to run.")
    parser.add_argument("--db-path", default=os.getenv("DATABASE_PATH", "tracker.db"), help="Path to the SQLite database file.")
    parser.add_argument("--backup-dir", default=os.getenv("BACKUP_DIR", "backups"), help="Directory where the backup file will be saved.")
    parser.add_argument("--backup-file", help="Backup file to restore from when using the restore command.")
    args = parser.parse_args(argv)

    if args.command == "backup":
        print(
            "WARNING: keep ENCRYPTION_KEY backed up separately; otherwise this database backup cannot decrypt record counts.",
            file=sys.stderr,
        )
        backup_path = backup_database(args.db_path, args.backup_dir)
        print(f"Backup created: {backup_path}")
        return

    if not args.backup_file:
        raise ValueError("--backup-file is required when running the restore command.")

    restore_database(args.db_path, args.backup_file)
    print(f"Database restored from: {args.backup_file}")


if __name__ == "__main__":
    main()
