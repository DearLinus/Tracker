import hashlib
import json
import os
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

import config


class RecoveryStorageError(RuntimeError):
    """Raised when external recovery snapshot state is missing, invalid, or inconsistent."""


def _get_fernet() -> Fernet:
    key = getattr(config, "ENCRYPTION_KEY", None)
    if not key:
        raise ValueError("Missing required environment variable: ENCRYPTION_KEY")
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise ValueError("ENCRYPTION_KEY must be a valid Fernet key.") from exc


class RecoveryStorage:
    """Encrypted file-backed storage for pending-deletion recovery snapshots."""

    def __init__(self, db_path: str | None = None):
        db_path = Path(db_path or config.DATABASE_PATH)
        storage_dir = (db_path.parent if db_path.parent != Path("") else Path(".")) / "recovery"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.storage_dir, 0o700)

    def _path_for_user(self, user_id: int) -> Path:
        token = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:16]
        return self.storage_dir / f"{token}.enc"

    def save_snapshot(self, user_id: int, data: dict) -> str:
        path = self._path_for_user(user_id)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.storage_dir, 0o700)

        payload = json.dumps(data, sort_keys=True).encode("utf-8")
        encrypted = _get_fernet().encrypt(payload)

        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(self.storage_dir))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encrypted)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, path)
            os.chmod(path, 0o600)
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

        return str(path)

    def load_snapshot(self, user_id: int):
        path = self._path_for_user(user_id)
        if not path.exists():
            raise RecoveryStorageError(f"Recovery snapshot missing for user {user_id}.")

        try:
            encrypted = path.read_bytes()
            decrypted = _get_fernet().decrypt(encrypted)
            snapshot = json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RecoveryStorageError(f"Recovery snapshot for user {user_id} is corrupted or unreadable.") from exc

        if not isinstance(snapshot, dict):
            raise RecoveryStorageError(f"Recovery snapshot for user {user_id} has an invalid structure.")

        return snapshot

    def delete_snapshot(self, user_id: int) -> bool:
        path = self._path_for_user(user_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, user_id: int) -> bool:
        return self._path_for_user(user_id).exists()
