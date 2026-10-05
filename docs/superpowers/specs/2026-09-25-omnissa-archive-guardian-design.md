# Specification: Omnissa Archive and Omnissa Guardian

Original date: 2026-09-25  
Updated: 2026-10-05  
Status: implemented  
Workspace: `C:\GitHub\Omnissas Guardian`

## 1. Purpose

A local copy of the public English documentation from docs.omnissa.com and of articles from kb.omnissa.com, for sites without internet. The content remains Omnissa's. This is not a public mirror.

Two uses of the same database:

| Use | Who runs it | What happens |
|---|---|---|
| Downloading the content | Whoever prepares the database | `discover` / `fetch` / `refresh` write to SQLite and to the image folder |
| Use at a customer site | An environment administrator | The Guardian window scans a log, matches an error to the database, and opens the archive locally |

Guardian's main purpose: a log path, local or UNC, comes in. An error line is matched to the KB articles stored locally. Search on public sites is a manual extra, off by default, and not part of the scan.

The archive and the Guardian window are English only, left to right. There is no language toggle.

## 2. Customer delivery

A customer has no BAT files and no Python.

First time: `dist\OmnissaGuardianSetup.exe`  
The installer lays out:

```
{autopf}\Omnissa Guardian\
  OmnissaGuardian.exe
  _internal\
  data\
    library\
      archive.sqlite
      inbox\
    assets\
```

The setup wizard is English.

The EXE carries the shield icon (`assets\omnissa-guardian.ico`): background `#2c2c3e`, shield `#f07a58`, mark `#e8b545`. The icon is on the file, on the shortcut, and on the window.

Clicking the shortcut opens the monitoring window and starts the archive server on `127.0.0.1:8765` only. Other computers on the network cannot reach it.

`dist\OmnissaGuardian` is the preliminary test copy. It is opened without running the installer. Its database is `dist\OmnissaGuardian\data\library\archive.sqlite`. An empty `data\archive.sqlite` beside the EXE is not the archive.

Once a month, on the computer that prepares the database:

```powershell
.\.venv\Scripts\python -m omnissa_archive refresh
.\.venv\Scripts\python installer\stage_library.py
```

`refresh` reads the sitemaps again and downloads only a new address or an address whose date changed. `stage_library.py` writes a consistent copy to `dist\package-staging\archive.sqlite`, without an open WAL file in the middle.

The customer places the new `archive.sqlite` in `data\library\inbox\`. The file is checked (SQLite signature and a `documents` table), copied to `data\library\archive.sqlite`, and the previous file is kept under `data\libraries\`. There is no reinstall and the program does not have to be closed. New images arrive with an update of `data\assets\`.

A repeated install does not overwrite a database that already exists. Uninstall does not delete the database or the images.

One HTML file for the whole archive is not suitable: the database and the images are larger than that. `python -m omnissa_archive package` still produces an internal copy folder `dist\Omnissa-Archive\`. That is not the package the customer installs.

Building the installer:

```powershell
.\.venv\Scripts\python installer\stage_library.py
.\.venv\Scripts\python -m PyInstaller build\pyinstaller\OmnissaGuardian.spec --noconfirm --distpath dist --workpath build\pyinstaller
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\OmnissaGuardian.iss
```

`stage_library.py` copies the live database as a consistent snapshot, without an open WAL file in the middle. After the EXE is rebuilt, the same snapshot is placed at `dist\OmnissaGuardian\data\library\archive.sqlite` for the test folder.

## 3. Archive

Local interface in English, left to right.

- Side menu: Home, KB articles, Documentation, Settings
- Home: two cubes, the five latest KB articles and the five latest documents
- Table: Date, KB number, Subject, Category (family · product · version · category)
- Filters: product family, product, version, category, from date, to date. Product and version may be a comma-separated list
- FTS search on the title and the text
- Settings: load a SQLite database

Palette: `#2c2c3e`, `#f07a58`, `#365565`, `#4d889d`, `#e8b545`, `#bebec6`.

The publication date on docs pages is `omnissa-datecreated`. On KB it is `article:published_time`. The text `Last updated:` at the start of a KB article is the update date stored in `updated_at`.

## 4. Guardian

A dark window in the style of a monitoring console. English only. Settings are stored in `data\guardian_config.json`. Language is not a setting.

Default paths come from KB 1027744 (Horizon log locations). They are correct when the process runs on that server. From a server with SMB access, paste a UNC path, for example `\\host\C$\ProgramData\Omnissa\Horizon\logs`. The account that runs the program is the account that reads the share. A password is not stored in the program.

Scan:

- Default interval 60 seconds, minimum 15
- The first scan of a file reads the content already there. Above 2MB, the last two megabytes are read
- After that, only what was appended is read
- A line is detected by error, exception, failed, failure, fatal, critical, warning
- The search takes words from the line, drops noise words, and ranks articles with FTS
- The alert shows a title, a date, an excerpt, and a `/read/{id}` link in the local archive

Guardian reads the same database. The `inbox` folder is checked from Guardian as well, not only from the archive screen.

The window: Live Monitor, History, Watch Dirs, KB Sources, Settings, Email, System Log. The Email tab does not send messages. Detections stay on the computer.

### Online documents

The KB Sources tab keeps a browser-search area, with the templates from the previous client:

| Name | Template |
|---|---|
| Omnissa KB | `https://kb.omnissa.com/s/global-search/{q}` |
| Omnissa TechZone | `https://techzone.omnissa.com/search#q={q}` |
| Broadcom Support | `https://support.broadcom.com/web/ecx/search#q={q}` |
| VMware Community | `https://community.broadcom.com/search?q={q}` |
| Reddit r/vmware | `https://www.reddit.com/r/vmware/search/?q={q}` |
| Google | `https://www.google.com/search?q=Omnissa+Horizon+{q}` |

`{q}` is the error text, up to 200 characters, after URL encoding.

The area is always shown. It is not checked during the log scan.

Settings has a **Search online documents** checkbox. It is stored as `online_search` in `data\guardian_config.json`, and it is off by default. Without the check, clicking **Search online** does not use the network.

When the box is checked, clicking **Search online** (on the tab or from a detection detail) first tries a short TCP connection to `kb.omnissa.com` on port 443. If the connection fails, no browser opens and the search stays on the local archive. If the connection succeeds, a search opens for each template.

Not included: sending to the cloud, an agent on every workstation, automatic repair, a diagnostic package for a vendor, or an automatic request to Omnissa sites during a scan.

## 5. Download and resume after a stop

Sources:

- docs: a sitemap index, English pages without a language prefix. The page body is `article .doc-body`. Metadata is read from the full page.
- KB: the SitemapGeneratorVF list. The article is rendered in Chrome through Playwright until `#article_content` and `article:published_time` appear. An article that is no longer available is not tried again.

The queue in `crawl_queue`: `pending`, `running`, `done`, `error`.  
`fetch` returns an interrupted `running` row to `pending`, and skips `done`. Up to three attempts for an error.

`refresh` is the periodic update: `discover` first, then `fetch`. `Open-Download.bat` runs only `fetch`. It continues an existing queue and does not read the sitemaps again, so it is not the monthly update.

During the sitemap phase every line is a summary, with no time and no title:

```text
docs sitemap-0001.xml english=65 new=0
docs revisions stamped=… changed=…
kb sitemap articles=… new=… stamped=… changed=…
```

`english` and `articles` are how many addresses were found in the map. `new` is how many of them were not already in the queue. `changed` is how many addresses had a changed `lastmod` and returned to `pending`.

The map `lastmod` is stored separately. On save, if `Last updated` is the same, the page body is not written again.

A download log line appears only later, and only for a page that is actually downloaded:

```text
YYYY-MM-DD HH:MM:SS docs|kb n/total KB id|— | title or status | saved=… done=… pending=… running=… error=…
```

The time is the local clock.

Polite rate: about 3 requests per second for documentation, and one KB article at a time with a pause. `robots.txt` is respected: no `/api/` and no `/search` for documentation, and no `/articles/` for KB. The articles themselves are taken from `/s/article/`.

## 6. Storage

SQLite with WAL and FTS5 on title and text.

`documents`: source, address, title, body, hash, product, family, version, category, publication date, update date, `sitemap_lastmod`.  
`crawl_queue`: address, status, attempts, `remote_lastmod`.  
Images and PDFs are in `data\assets\`, and the local HTML points to them.

On the development computer the live database is `data\archive.sqlite`. At a customer site it is `data\library\archive.sqlite`. The test folder uses that same customer path under `dist\OmnissaGuardian\data\library\archive.sqlite`.

## 7. Moving to another computer

`data\`, `.venv\`, `build\`, and `dist\` are not in Git. The code is.

To continue a download on a new computer, copy `data\archive.sqlite` after `PRAGMA wal_checkpoint(TRUNCATE)`, and `data\assets\`. Without the database the queue is empty. Then create a new `.venv` with the local Python and run `refresh` or `fetch`. The commands are in `README.md`.

A `.venv` copied from another computer or another user is not usable. `pyvenv.cfg` stores the path of the Python that created it, and the editable install stores the source path. On the new computer, create a new environment.

## 8. Success

- A customer installs from one file, without Python, and sees the icon on the program file.
- A monthly database replacement loads without a restart.
- A UNC path with an error already in the log shows an article from the local database on the first scan.
- A download that stops in the middle continues from the queue on this computer or on a computer that received `data\`.
- A monthly update with `refresh` prints sitemap summaries first. Lines with a time and a title appear only for pages that changed or were added.
- A log scan does not contact Omnissa sites. Online search opens only after the setting is checked, an explicit click, and a connection to `kb.omnissa.com`.
- The test folder `dist\OmnissaGuardian` shows the same English interface and the staged database, without running the installer.
