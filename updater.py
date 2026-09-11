import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def wait_for_process_exit(pid: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while process_exists(pid) and time.time() < deadline:
        time.sleep(0.2)

    if process_exists(pid):
        raise RuntimeError("The main application did not close in time.")


def validate_zip(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad_file = archive.testzip()
        if bad_file is not None:
            raise RuntimeError(f"The update ZIP is corrupted: {bad_file}")

        files = [name for name in archive.namelist() if not name.endswith("/")]
        if not files:
            raise RuntimeError("The update ZIP is empty.")

        for name in files:
            normalized = Path(name)
            if normalized.is_absolute() or ".." in normalized.parts:
                raise RuntimeError(f"Unsafe path in update ZIP: {name}")


def backup_user_data(app_dir: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("tracker.db", "tracker_settings.json"):
        source = app_dir / filename
        if source.exists():
            shutil.copy2(source, backup_dir / filename)


def extract_update(zip_path: Path, extract_dir: Path) -> list[Path]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    extracted_files = [p for p in extract_dir.rglob("*") if p.is_file()]
    if not extracted_files:
        raise RuntimeError("The update ZIP contained no files.")

    # Releases are intentionally flat (main.py, gui.py, etc.).
    # This prevents accidentally installing a nested folder.
    for source in extracted_files:
        relative = source.relative_to(extract_dir)
        if len(relative.parts) != 1:
            raise RuntimeError(
                "The update ZIP must contain application files at its root. "
                f"Unexpected path: {relative}"
            )

    return extracted_files


def replace_application(extracted_files: list[Path], extract_dir: Path, app_dir: Path) -> None:
    for source in extracted_files:
        relative = source.relative_to(extract_dir)
        destination = app_dir / relative

        # Never let an update replace the user's data files.
        if destination.name in {"tracker.db", "tracker_settings.json"}:
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def launch_application(app_dir: Path) -> None:
    main_py = app_dir / "main.py"
    if not main_py.exists():
        raise RuntimeError("main.py was not found after the update.")

    subprocess.Popen(
        [sys.executable, str(main_py)],
        cwd=app_dir,
        start_new_session=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily Tracker updater")
    parser.add_argument("--zip", required=True)
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--expected-sha256", default="")
    args = parser.parse_args()

    zip_path = Path(args.zip).resolve()
    app_dir = Path(args.app_dir).resolve()

    try:
        if not zip_path.exists():
            raise RuntimeError("Downloaded update file was not found.")
        if not app_dir.exists():
            raise RuntimeError("Application directory was not found.")

        if args.expected_sha256:
            actual = sha256_file(zip_path)
            expected = args.expected_sha256.strip().lower()
            if actual != expected:
                raise RuntimeError(
                    "SHA-256 verification failed. The update was not installed."
                )

        validate_zip(zip_path)
        wait_for_process_exit(args.pid)

        backup_root = app_dir / "update_backups"
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = backup_root / timestamp
        backup_user_data(app_dir, backup_dir)

        with tempfile.TemporaryDirectory(prefix="daily_tracker_extract_") as temp_dir:
            extract_dir = Path(temp_dir)
            extracted_files = extract_update(zip_path, extract_dir)

            # Back up files that will be replaced so a failed update can be rolled back.
            rollback_dir = extract_dir / "rollback"
            for source in extracted_files:
                relative = source.relative_to(extract_dir)
                destination = app_dir / relative
                if destination.exists() and destination.name not in {"tracker.db", "tracker_settings.json"}:
                    rollback_target = rollback_dir / relative
                    rollback_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, rollback_target)

            try:
                replace_application(extracted_files, extract_dir, app_dir)
            except Exception:
                for old_file in rollback_dir.rglob("*"):
                    if old_file.is_file():
                        relative = old_file.relative_to(rollback_dir)
                        destination = app_dir / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(old_file, destination)
                raise

        zip_path.unlink(missing_ok=True)

        launch_application(app_dir)
        return 0

    except Exception as error:
        print(f"Update failed: {error}", file=sys.stderr)
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())