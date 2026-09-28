"""Write a consistent snapshot of the live archive for the installer and the test copy."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "archive.sqlite"
TARGET = ROOT / "dist" / "package-staging" / "archive.sqlite"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        TARGET.unlink()
    source = sqlite3.connect(SOURCE)
    target = sqlite3.connect(TARGET)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    print(TARGET)
    print(TARGET.stat().st_size)


if __name__ == "__main__":
    main()
