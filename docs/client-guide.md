# Client guide — Omnissa archive and Omnissa Guardian

A local copy for reading and monitoring on disconnected sites. **This is not a public mirror.** The content belongs to Omnissa and is for internal use.

Customers receive one installer. The BAT files and Python stay on the computer that downloads the content.

The archive and the Guardian window are English only.

## What the customer receives

| File | When |
|---|---|
| `OmnissaGuardianSetup.exe` | First time. Installs the program, a default database, and the image folder |
| `archive.sqlite` | Monthly or quarterly, when a newer database is ready |

After installation there is an **Omnissa Guardian** shortcut with the shield icon. Opening it starts:

- the log-monitoring window
- the archive on this computer only: [http://127.0.0.1:8765/](http://127.0.0.1:8765/)

Monitoring does not need an external browser. The archive itself is read in a browser at the local address.

## Where the files are after installation

The default location is `C:\Program Files\Omnissa Guardian\`:

| Path | What it is |
|---|---|
| `OmnissaGuardian.exe` | The program. The icon is on the file and on the shortcut |
| `data\library\archive.sqlite` | The active database |
| `data\assets\` | Article images. Without this folder the text opens and the images are missing |
| `data\library\inbox\` | Put a new database here |
| `data\guardian_config.json` | Scan interval, log paths, and online search |

Uninstall leaves the database and the images in place.

## Monitoring a log on a UNC path

This is the product action: a log path goes in, and an article from the local archive comes out.

1. On the **Watch Dirs** tab, paste a path, for example  
   `\\cs01.corp.local\C$\ProgramData\Omnissa\Horizon\logs`
2. Each path, including the ones that come with the program, is one row. The pencil icon edits the name and path. The trash icon removes the path.
3. Click **Start Monitoring**.
4. A line with error, exception, failed, or fatal is checked against the database.
5. The window shows the title, the date, an excerpt, and a link that opens in the archive.

The account that runs Guardian must be able to read the path. A local path on a Connection Server works the same way.

The first scan of a file reads what is already in it. A file larger than 2MB is read from the end, the last two megabytes. After that only new lines are read, and a line that was already reported does not appear again. The default interval is 60 seconds.

The default paths on the screen are Horizon paths from KB 1027744. They are useful when the program runs on the server itself. From a management server with SMB access, use a UNC path.

## Online documents

The **KB Sources** tab has a search area for public sites: Omnissa KB, TechZone, Broadcom, Community, Reddit, and Google. The scan does not contact them.

To search there:

1. In Settings, check **Search online documents** and save.
2. Click **Search online** on the tab, or from the detail of a detection.
3. When the network can reach `kb.omnissa.com`, the searches open in the browser. Without a network, a message is shown and the match stays on the local archive.

Without the Settings checkbox, the button does not use the network.

## Updating a customer's database

1. Copy the new `archive.sqlite` into `data\library\inbox\` of the installation.
2. The archive and Guardian load it without closing the program.
3. If article images were added, update `data\assets\` as well.

A database can also be loaded from the archive Settings page. That page expects a consistent SQLite file. Copying the live download file while it is open can be rejected, and the reader then stays on the database it already had.

## Archive: search and filters

The local address has a side menu, two home cubes (latest KB articles and latest documents), and a table:

Date, KB number, Subject, Category.

Filters are product family, product, version, category, and a date range. The search box finds a word inside the documents.

## The computer that downloads the content

The download stays with the person who prepares the database. A customer does not run it.

Once a month:

```powershell
.\.venv\Scripts\python -m omnissa_archive refresh
.\.venv\Scripts\python installer\stage_library.py
```

`Open-Download.bat` only continues a download that is already queued. It does not check what changed on the site.

- The first lines are short sitemap summaries, for example `docs sitemap-0001.xml english=65 new=0`. They have no time and no title.
- `new=0` means those addresses were already in the database.
- A line with a time, a title, and a KB number appears later, only for a new page or a page whose date changed.
- A `done` page is not downloaded again.
- Closing in the middle returns the in-progress page to the queue. The next run continues from there.

`stage_library.py` writes `dist\package-staging\archive.sqlite`. That is the file to copy to a customer.

For a preliminary test without installing, the same snapshot belongs in `dist\OmnissaGuardian\data\library\archive.sqlite`. The folder `dist\OmnissaGuardian` is the copy opened directly. It is not the installer.

Installing the development environment and copying `data\` to another computer are described in `README.md`.
