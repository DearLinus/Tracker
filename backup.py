import os
import shutil
from datetime import datetime


def backup_database(db_path: str, backup_dir: str) -> str:
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"tracker_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    shutil.copy2(db_path, backup_path)

    legacy_backup_path = os.path.join(backup_dir, os.path.basename(db_path))
    if not os.path.exists(legacy_backup_path):
        shutil.copy2(db_path, legacy_backup_path)

    return backup_path


def restore_database(db_path: str, backup_path: str) -> None:
    shutil.copy2(backup_path, db_path)
