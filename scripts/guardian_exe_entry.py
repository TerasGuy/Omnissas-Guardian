"""PyInstaller entry for Omnissa Guardian desktop."""

from pathlib import Path
import sys


def main() -> int:
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
        # Prefer project root when EXE lives in dist/
        if root.name.lower() == "dist":
            root = root.parent
    else:
        root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from omnissa_archive.guardian_desktop import run_desktop

    run_desktop(data_dir, reader_base="http://127.0.0.1:8765")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
