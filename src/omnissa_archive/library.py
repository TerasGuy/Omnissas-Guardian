"""Portable library layout and live SQLite reload for customer packages."""

from __future__ import annotations

import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SQLITE_HEADER = b"SQLite format 3\x00"


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_sqlite_database(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            return handle.read(16).startswith(SQLITE_HEADER)
    except OSError:
        return False


def has_documents_table(path: Path) -> bool:
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            conn.execute("SELECT 1 FROM documents LIMIT 1").fetchone()
        finally:
            conn.close()
        return True
    except sqlite3.Error:
        return False


def validate_database(path: Path) -> Path:
    if not is_sqlite_database(path):
        raise ValueError("הקובץ אינו מסד SQLite")
    if not has_documents_table(path):
        raise ValueError("במסד אין טבלת documents")
    return path


def file_stamp(path: Path) -> tuple[int, int] | None:
    if not path.is_file():
        return None
    stat = path.stat()
    return int(stat.st_mtime_ns), int(stat.st_size)


def default_database_candidates(data_dir: Path) -> list[Path]:
    return [
        data_dir / "library" / "archive.sqlite",
        data_dir / "archive.sqlite",
        data_dir.parent / "library" / "archive.sqlite",
    ]


def resolve_default_database(data_dir: Path) -> Path:
    for candidate in default_database_candidates(data_dir):
        if candidate.is_file():
            return candidate
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "archive.sqlite"


def assets_root_for(database: Path, data_dir: Path) -> Path:
    sibling = database.parent / "assets"
    if sibling.is_dir():
        return sibling
    package_assets = database.parent.parent / "assets"
    if database.parent.name == "library" and package_assets.is_dir():
        return package_assets
    return data_dir / "assets"


def inbox_dir(data_dir: Path) -> Path:
    path = data_dir / "library" / "inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def libraries_dir(data_dir: Path) -> Path:
    path = data_dir / "libraries"
    path.mkdir(parents=True, exist_ok=True)
    return path


def newest_inbox_database(data_dir: Path) -> Path | None:
    folder = data_dir / "library" / "inbox"
    if not folder.is_dir():
        return None
    candidates = sorted(
        (path for path in folder.iterdir() if path.suffix.lower() in {".sqlite", ".db"} and path.is_file()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    for path in candidates:
        if is_sqlite_database(path) and has_documents_table(path):
            return path
    return None


@dataclass
class ReloadEvent:
    path: Path
    notice: str


class LibraryWatcher:
    """Detect SQLite replacement or content change without restarting the process."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._path: Path | None = None
        self._stamp: tuple[int, int] | None = None
        self.last_reload_notice: str = ""
        self.last_reload_at: str = ""

    def bind(self, path: Path) -> None:
        self._path = path
        self._stamp = file_stamp(path)

    def poll(self, current: Path) -> ReloadEvent | None:
        inbox = newest_inbox_database(self.data_dir)
        if inbox is not None and (self._path is None or inbox.resolve() != current.resolve()):
            target = self._promote_inbox(inbox)
            self.bind(target)
            notice = f"נטען מסד חדש מהתיבה: {target.name}"
            self.last_reload_notice = notice
            self.last_reload_at = utcnow()
            return ReloadEvent(target, notice)

        stamp = file_stamp(current)
        if self._path is None or self._path.resolve() != current.resolve():
            self.bind(current)
            return None
        if stamp is None:
            return None
        if self._stamp is None:
            self._stamp = stamp
            return None
        if stamp != self._stamp:
            self._stamp = stamp
            notice = f"המסד עודכן בלי ריסטארט: {current.name}"
            self.last_reload_notice = notice
            self.last_reload_at = utcnow()
            return ReloadEvent(current, notice)
        return None

    def _promote_inbox(self, inbox: Path) -> Path:
        validate_database(inbox)
        library = self.data_dir / "library"
        library.mkdir(parents=True, exist_ok=True)
        target = library / "archive.sqlite"
        backup = libraries_dir(self.data_dir) / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-inbox-{inbox.name}"
        if target.is_file():
            shutil.copy2(target, backup)
        shutil.copy2(inbox, target)
        inbox.unlink(missing_ok=True)
        return target


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def install_uploaded_database(data_dir: Path, filename: str, payload: bytes) -> Path:
    if not payload.startswith(SQLITE_HEADER):
        raise ValueError("הקובץ אינו מסד SQLite")
    stem = _SAFE_NAME.sub("_", Path(filename or "archive.sqlite").name) or "archive.sqlite"
    if not stem.lower().endswith((".sqlite", ".db")):
        stem += ".sqlite"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = libraries_dir(data_dir) / f"{stamp}-{stem}"
    target.write_bytes(payload)
    try:
        validate_database(target)
    except ValueError:
        target.unlink(missing_ok=True)
        raise
    library = data_dir / "library"
    library.mkdir(parents=True, exist_ok=True)
    live = library / "archive.sqlite"
    shutil.copy2(target, live)
    return live


def prepare_customer_package(source_data: Path, output_dir: Path) -> Path:
    """Copy the current archive into a portable customer folder."""
    source_db = resolve_default_database(source_data)
    if not source_db.is_file():
        raise FileNotFoundError(f"missing database: {source_db}")
    validate_database(source_db)
    package = output_dir / "Omnissa-Archive"
    library = package / "library"
    assets = package / "assets"
    library.mkdir(parents=True, exist_ok=True)
    if assets.exists():
        shutil.rmtree(assets)
    source_assets = assets_root_for(source_db, source_data)
    if source_assets.is_dir():
        shutil.copytree(source_assets, assets)
    else:
        assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, library / "archive.sqlite")
    inbox_dir(package)
    bat = package / "Open-Archive.bat"
    bat.write_text(
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "if exist .venv\\Scripts\\python.exe (\r\n"
        "  .\\.venv\\Scripts\\python -m omnissa_archive serve --data-dir . --port 8765\r\n"
        ") else if exist ..\\.venv\\Scripts\\python.exe (\r\n"
        "  ..\\.venv\\Scripts\\python -m omnissa_archive serve --data-dir . --port 8765\r\n"
        ") else (\r\n"
        "  echo Install the project venv or place a portable Python next to this package.\r\n"
        "  pause\r\n"
        ")\r\n",
        encoding="utf-8",
    )
    readme = package / "README-he.txt"
    readme.write_text(
        "חבילת ארכיון Omnissa ללקוח\r\n"
        "========================\r\n"
        "הפצה ללקוח היא קובץ ההתקנה OmnissaGuardianSetup.exe.\r\n"
        "התיקייה הזו היא עותק פנימי של המסד והתמונות.\r\n"
        "1. הארכיון נפתח בכתובת http://127.0.0.1:8765/ יחד עם חלון Guardian.\r\n"
        "2. לעדכון חודשי או רבעוני: העתיקו archive.sqlite חדש אל data\\library\\inbox\\\r\n"
        "   אחרי התקנה, או אל library\\inbox\\ בחבילה הזו.\r\n"
        "   המסד נטען בלי ריסטארט.\r\n"
        "3. תמונות נשמרות בתיקיית assets. בלי התיקייה המאמר נפתח והתמונות חסרות.\r\n",
        encoding="utf-8",
    )
    return package
