# Omnissa archive and Omnissa Guardian

A **local** copy of Omnissa documentation and KB articles, for disconnected sites.  
**This is not a public mirror.** The content belongs to Omnissa.

Implemented specification: [`docs/superpowers/specs/2026-09-25-omnissa-archive-guardian-design.md`](docs/superpowers/specs/2026-09-25-omnissa-archive-guardian-design.md)  
Client guide: [`docs/client-guide.md`](docs/client-guide.md)

The archive and the Guardian window are English only. There is no language toggle.

## What each program does

- **Archive** — search, filter by product, family, version, category, and date, and read documents offline. The table includes the KB number (for example `1027744`). Documentation pages without a number are shown with a dash.
- **Guardian** — a desktop window for log monitoring. A local or UNC path is scanned, error lines are matched to the local database, and a relevant article is shown. On startup Guardian also starts the archive server at `http://127.0.0.1:8765/`. Online document search is off by default. It opens only after the setting is checked, **Search online** is clicked, and the network can reach `kb.omnissa.com`.

The `Open-*.bat` files are shortcuts for the development computer. Customers receive the installer, not a BAT file. `Open-Guardian.bat` starts `dist\OmnissaGuardian\OmnissaGuardian.exe`, the folder used for a preliminary test without installing.

## What goes into Git and what is copied separately

Git stores the code, the tests, the icon, the installer script, and the documents.  
The database, the images, the Python environment, and the build output **are not** in Git:

| Path | In Git? | What it is for |
|---|---|---|
| `src\`, `tests\`, `installer\`, `assets\omnissa-guardian.ico` | Yes | The code and the icon |
| `data\archive.sqlite` (and `-wal` / `-shm` when they exist) | No | The database and the queue. Without it the download starts over |
| `data\assets\` | No | Article images |
| `.venv\` | No | Created again on the target computer |
| `dist\`, `build\` | No | EXE, test folder, and installer. Built again |

## Moving to another computer

1. Stop the download (`fetch`) so the database is not written during the copy.
2. Fold the WAL into one database file:

```powershell
.\.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect(r'data/archive.sqlite'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)'); c.close()"
```

3. Copy the whole project folder, especially `data\archive.sqlite` and `data\assets\`. The code can go through Git, and the `data\` folder separately (it is in `.gitignore`).
4. On the new computer, from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m omnissa_archive fetch
```

Python 3.11 or newer is required (development runs on 3.14), and Google Chrome is used to render KB articles.  
`fetch` continues from the queue inside the database. An address in the `done` state is not downloaded again.  
A virtual environment copied from another computer does not run: create a new `.venv` with the local Python.

Rebuilding the program and the installer also needs [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```powershell
.\.venv\Scripts\python installer\stage_library.py
.\.venv\Scripts\python -m PyInstaller build\pyinstaller\OmnissaGuardian.spec --noconfirm --distpath dist --workpath build\pyinstaller
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\OmnissaGuardian.iss
```

The installer result is `dist\OmnissaGuardianSetup.exe`. The setup wizard is English. After PyInstaller, put the staged database at `dist\OmnissaGuardian\data\library\archive.sqlite` so the test folder opens the archive instead of an empty database created beside the EXE.

## Commands

```powershell
.\.venv\Scripts\python -m omnissa_archive discover
.\.venv\Scripts\python -m omnissa_archive fetch
.\.venv\Scripts\python -m omnissa_archive refresh
.\.venv\Scripts\python -m omnissa_archive serve --port 8765
.\.venv\Scripts\python -m omnissa_archive guardian
.\.venv\Scripts\python -m omnissa_archive package --output dist
.\.venv\Scripts\python -m omnissa_archive search "Horizon logs"
```

The monthly update is `refresh`, not `Open-Download.bat`. That file continues an existing queue without reading the sitemaps again.

`refresh` first prints a summary for each sitemap, with no time and no title, for example `docs sitemap-0001.xml english=65 new=0`. `new=0` means those addresses are already in the database. At the end of that phase, `changed` is printed for documentation and for the KB sitemap. Only after that, and only for a new page or a page whose date changed, a download line is printed with the local time, `docs` or `kb`, the position in the total, the KB number, the title, and the `saved/done/pending/running/error` summary.

After the download finishes, a consistent copy for a customer:

```powershell
.\.venv\Scripts\python installer\stage_library.py
```

The file is written to `dist\package-staging\archive.sqlite`. On a customer computer it goes in `data\library\inbox\`.
