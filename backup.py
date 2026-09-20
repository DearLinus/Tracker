import os
import sqlite3
from datetime import datetime


def backup_database(db_path: str, backup_dir: str) -> str:
    os.makedirs(backup_dir, exist_ok=True)

    if not os.path.exists(db_path):
        sqlite3.connect(db_path).close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"tracker_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

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
