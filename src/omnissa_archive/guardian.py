"""Omnissa Guardian — local log monitoring with archive-backed suggestions."""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from omnissa_archive.db import connect, init_db
from omnissa_archive.library import assets_root_for, resolve_default_database
from omnissa_archive.solutions import suggest_solutions

# Defaults from archived KB 1027744 (Location of Horizon View log files).
DEFAULT_LOG_TARGETS = [
    {
        "id": "connection-server",
        "label": "Connection / Replica Server",
        "path": r"%ProgramData%\Omnissa\Horizon\logs",
        "enabled": True,
    },
    {
        "id": "agent-windows",
        "label": "Horizon Agent (Windows)",
        "path": r"%ProgramData%\Omnissa\Horizon\logs",
        "enabled": True,
    },
    {
        "id": "agent-user",
        "label": "Agent (משתמש)",
        "path": r"%TEMP%\omnissa-%USERNAME%",
        "enabled": False,
    },
    {
        "id": "blast-service",
        "label": "Blast Service",
        "path": r"%ProgramData%\Omnissa\Horizon\logs\Blast-Service.log",
        "enabled": True,
    },
    {
        "id": "blast-worker",
        "label": "Blast Worker",
        "path": r"%ProgramData%\Omnissa\Horizon\logs\Blast-Worker-SessionIdX.log",
        "enabled": False,
    },
    {
        "id": "logon-monitor",
        "label": "Logon Monitor",
        "path": r"%ProgramData%\Omnissa\Logon Monitor\Logs",
        "enabled": False,
    },
    {
        "id": "guest-customization",
        "label": "Guest Customization",
        "path": r"%SystemDrive%\Windows\Temp\Omnissa\Horizon-viewcomposer-ga-new.log",
        "enabled": False,
    },
]

ERROR_RE = re.compile(
    r"\b(error|exception|failed|failure|fatal|critical|unable to|cannot )\b",
    re.I,
)
PAGE_CSS = """
:root { --ink:#2c2c3e; --coral:#f07a58; --teal:#365565; --teal-mid:#4d889d; --gold:#e8b545; --line:#bebec6; --paper:#f4f4f6; }
* { box-sizing: border-box; }
body { margin:0; font-family:"Segoe UI",Arial,sans-serif; background:radial-gradient(900px 420px at 70% -80px,#f8d2c6,transparent 55%),var(--paper); color:var(--ink); }
.shell { display:flex; min-height:100vh; }
nav.side { width:220px; flex:none; background:var(--ink); padding:28px 14px; }
nav.side a { display:block; color:#bebec6; text-decoration:none; padding:12px 14px; border-radius:12px; margin-bottom:6px; font-weight:600; }
nav.side a.active, nav.side a:hover { background:var(--teal); color:white; }
.content { flex:1; min-width:0; padding:24px 28px 48px; }
h1 { margin:0 0 6px; font-size:28px; letter-spacing:-.04em; }
.sub { color:var(--teal); margin:0 0 18px; }
.panel { background:white; border:1px solid var(--line); border-radius:22px; padding:16px 18px; margin-bottom:16px; box-shadow:0 14px 36px rgba(44,44,62,.05); }
.status-bar { display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
.pill { display:inline-flex; gap:8px; align-items:center; padding:8px 12px; border-radius:999px; background:var(--paper); color:var(--teal); font-size:13px; font-weight:700; }
.dot { width:8px; height:8px; border-radius:50%; background:var(--teal-mid); }
.dot.ok { background:#3d9a78; }
.dot.warn { background:var(--gold); }
.dot.alert { background:var(--coral); }
.grid-2 { display:grid; grid-template-columns:1.05fr 1fr; gap:16px; }
.path-row { display:grid; grid-template-columns:28px 1fr auto; gap:10px; align-items:start; padding:12px 0; border-bottom:1px solid #ececef; }
.path-row:last-child { border-bottom:0; }
.path-row code { display:block; margin-top:4px; color:var(--teal); font-size:12px; word-break:break-all; }
button, .btn { background:var(--coral); color:white; border:0; border-radius:999px; padding:10px 18px; font-weight:700; cursor:pointer; text-decoration:none; display:inline-block; }
button.ghost, a.ghost { background:transparent; color:var(--teal); }
input[type=text], input[type=number] { width:100%; padding:10px 12px; border:0; border-radius:12px; background:var(--paper); font:inherit; }
label span { display:block; color:var(--teal); font-size:11px; font-weight:700; margin-bottom:6px; }
.alert { border:1px solid var(--line); border-radius:18px; padding:14px 16px; margin-bottom:12px; background:linear-gradient(#fff,#fff) padding-box, linear-gradient(160deg,#f07a58,#f6e3b0) border-box; }
.alert .meta { color:var(--teal); font-size:12px; margin-bottom:6px; }
.log { font-family:Consolas,"Courier New",monospace; font-size:12px; background:var(--paper); border-radius:10px; padding:10px 12px; margin:8px 0 12px; direction:ltr; text-align:left; }
.suggest h3 { margin:0 0 4px; font-size:15px; }
.suggest p { margin:0; color:var(--teal); font-size:13px; line-height:1.45; }
.note { color:var(--teal); font-size:12px; }
@media (max-width:980px){ .shell{flex-direction:column;} nav.side{width:auto;} .grid-2{grid-template-columns:1fr;} }
"""


def expand_path(raw: str) -> str:
    return os.path.expandvars(os.path.expanduser(raw or ""))


def path_status(raw: str) -> str:
    expanded = expand_path(raw)
    if not expanded:
        return "ריק"
    path = Path(expanded)
    if any(ch in expanded for ch in "*?"):
        parent = path.parent if path.parent != path else Path(".")
        return "תבנית" if parent.exists() else "חסר"
    if path.is_file() or path.is_dir():
        return "נגיש"
    if expanded.startswith("\\\\"):
        return "UNC"
    return "חסר"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class GuardianApp:
    def __init__(self, data_dir: Path, reader_base: str = "http://127.0.0.1:8765") -> None:
        self.data_dir = data_dir
        self.reader_base = reader_base.rstrip("/")
        self.config_path = data_dir / "guardian_config.json"
        self.state = self._load_config()
        self.alerts: list[dict] = []
        self.offsets: dict[str, int] = {}
        self.last_scan_at = ""
        self.last_scan_error = ""
        self.running = True
        self._lock = threading.Lock()
        self._stop = threading.Event()
        db = resolve_default_database(data_dir)
        conn = connect(db)
        init_db(conn)
        conn.close()

    def _load_config(self) -> dict:
        if self.config_path.is_file():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        else:
            data = {}
        targets = data.get("targets") or DEFAULT_LOG_TARGETS
        extras = data.get("extra_paths") or []
        return {
            "interval_seconds": int(data.get("interval_seconds") or 60),
            "targets": targets,
            "extra_paths": extras,
            "running": bool(data.get("running", True)),
        }

    def save_config(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def database_path(self) -> Path:
        return resolve_default_database(self.data_dir)

    def _conn(self) -> sqlite3.Connection:
        conn = connect(self.database_path())
        init_db(conn)
        return conn

    def enabled_paths(self) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        for target in self.state["targets"]:
            if target.get("enabled"):
                items.append((target.get("label") or target.get("id") or "log", target.get("path") or ""))
        for index, raw in enumerate(self.state.get("extra_paths") or [], start=1):
            if raw:
                items.append((f"נתיב נוסף {index}", raw))
        return items

    def iter_log_files(self, raw: str) -> list[Path]:
        expanded = expand_path(raw)
        if not expanded:
            return []
        path = Path(expanded)
        if any(ch in expanded for ch in "*?"):
            return sorted(path.parent.glob(path.name)) if path.parent.exists() else []
        if path.is_file():
            return [path]
        if path.is_dir():
            files: list[Path] = []
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in {".log", ".txt", ""}:
                    files.append(child)
                if len(files) >= 40:
                    break
            return files
        return []

    def scan_once(self) -> int:
        found = 0
        try:
            for label, raw in self.enabled_paths():
                for file_path in self.iter_log_files(raw):
                    found += self._scan_file(label, file_path)
            self.last_scan_at = _utcnow()
            self.last_scan_error = ""
        except OSError as exc:
            self.last_scan_error = str(exc)
        return found

    def _scan_file(self, label: str, path: Path) -> int:
        key = str(path)
        try:
            size = path.stat().st_size
        except OSError:
            return 0
        if key not in self.offsets:
            # First sighting: baseline at EOF so only new lines generate alerts.
            self.offsets[key] = size
            return 0
        offset = self.offsets[key]
        if offset > size:
            offset = 0
        if size == offset:
            return 0
        added = 0
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(offset)
                chunk = handle.read()
                new_offset = handle.tell()
        except OSError:
            return 0
        self.offsets[key] = new_offset
        for line in chunk.splitlines():
            if not ERROR_RE.search(line):
                continue
            alert = self._make_alert(label, path, line.strip())
            with self._lock:
                self.alerts.insert(0, alert)
                self.alerts = self.alerts[:80]
            added += 1
        return added

    def _make_alert(self, label: str, path: Path, line: str) -> dict:
        conn = self._conn()
        try:
            suggestions = suggest_solutions(conn, line, reader_base=self.reader_base)
        finally:
            conn.close()
        return {
            "at": _utcnow(),
            "label": label,
            "path": str(path),
            "line": line[:500],
            "suggestions": suggestions,
        }

    def start_worker(self) -> None:
        def loop() -> None:
            while not self._stop.is_set():
                if self.state.get("running", True):
                    self.scan_once()
                wait = max(15, int(self.state.get("interval_seconds") or 60))
                self._stop.wait(wait)

        thread = threading.Thread(target=loop, name="guardian-scan", daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop.set()

    def home_page(self) -> bytes:
        with self._lock:
            alerts = list(self.alerts[:12])
        open_count = len(alerts)
        status_dot = "alert" if open_count else "ok"
        status_text = f"{open_count} התראות" if open_count else "אין התראות פתוחות"
        scan_text = self.last_scan_at or "עדיין לא"
        body_paths = []
        for target in self.state["targets"]:
            raw = target.get("path") or ""
            checked = " checked" if target.get("enabled") else ""
            status = path_status(raw)
            body_paths.append(
                '<div class="path-row">'
                f'<input type="checkbox" name="enable_{html.escape(target["id"])}" value="1"{checked}>'
                f"<div><strong>{html.escape(target.get('label') or '')}</strong>"
                f"<code>{html.escape(raw)}</code></div>"
                f'<span class="pill"><span class="dot {"ok" if status == "נגיש" else "warn"}"></span>{html.escape(status)}</span>'
                "</div>"
            )
        for raw in self.state.get("extra_paths") or []:
            status = path_status(raw)
            body_paths.append(
                '<div class="path-row">'
                '<input type="checkbox" checked disabled>'
                f"<div><strong>נתיב נוסף / UNC</strong><code>{html.escape(raw)}</code></div>"
                f'<span class="pill"><span class="dot {"ok" if status == "נגיש" else "warn"}"></span>{html.escape(status)}</span>'
                "</div>"
            )
        alert_html = []
        for alert in alerts:
            suggestions = alert.get("suggestions") or []
            if suggestions:
                top = suggestions[0]
                suggest = (
                    "<div class='suggest'>"
                    f"<div><h3>{html.escape(top['title'])}</h3>"
                    f"<p>{html.escape(top['published_at'] or 'ללא תאריך')} · {html.escape(top['excerpt'][:180])}</p></div>"
                    f"<a class='btn' href=\"{html.escape(top['reader_link'])}\" target='_blank' rel='noopener'>פתח בארכיון</a>"
                    "</div>"
                )
            else:
                suggest = (
                    "<div class='suggest'><div><h3>לא נמצאה התאמה חזקה</h3>"
                    "<p>אפשר לחפש ידנית בארכיון.</p></div>"
                    f"<a class='ghost' href=\"{html.escape(self.reader_base + '/search?q=' + quote(alert['line'][:80]))}\" target='_blank' rel='noopener'>חיפוש בארכיון</a></div>"
                )
            alert_html.append(
                f"<div class='alert'><div class='meta'>{html.escape(alert['at'])} · {html.escape(alert['label'])}</div>"
                f"<div class='log'>{html.escape(alert['line'])}</div>{suggest}</div>"
            )
        if not alert_html:
            alert_html.append('<div class="panel"><p class="note">עדיין אין התראות. הסריקה רצה ברקע.</p></div>')
        running = self.state.get("running", True)
        page = f"""<!DOCTYPE html>
<html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omnissa Guardian</title><style>{PAGE_CSS}</style>
<meta http-equiv="refresh" content="30"></head><body><div class="shell">
<nav class="side">
  <a class="active" href="/">Guardian</a>
  <a href="{html.escape(self.reader_base)}/" target="_blank" rel="noopener">ארכיון</a>
</nav>
<div class="content">
<h1>Omnissa Guardian</h1>
<p class="sub">ניטור לוגים מקומי ו־UNC · התראות · הצעת פתרון מהארכיון</p>
<div class="panel status-bar">
  <span class="pill"><span class="dot {"ok" if running else "warn"}"></span>{"סריקה פעילה" if running else "סריקה מושהית"}</span>
  <span class="pill">מרווח: {int(self.state.get("interval_seconds") or 60)} שניות</span>
  <span class="pill">סריקה אחרונה: {html.escape(scan_text)}</span>
  <span class="pill"><span class="dot {status_dot}"></span>{html.escape(status_text)}</span>
  <span class="pill">מסד: {html.escape(self.database_path().name)}</span>
</div>
<div class="grid-2">
  <div class="panel">
    <form method="post" action="/settings">
      <div class="status-bar" style="margin-bottom:8px"><strong>מיקומי לוגים</strong></div>
      <p class="note">ברירות מחדל לפי KB 1027744. אפשר להוסיף נתיב מקומי או UNC.</p>
      {''.join(body_paths)}
      <div style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <label><span>מרווח סריקה (שניות)</span><input type="number" name="interval" min="15" step="15" value="{int(self.state.get('interval_seconds') or 60)}"></label>
        <label><span>נתיב נוסף / UNC</span><input type="text" name="extra" placeholder="\\\\server\\share\\logs או C:\\logs"></label>
      </div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button type="submit" name="action" value="save">שמירה</button>
        <button type="submit" name="action" value="{"pause" if running else "resume"}">{("השהיה" if running else "המשך")}</button>
        <button type="submit" name="action" value="scan">סריקה עכשיו</button>
      </div>
    </form>
  </div>
  <div>
    <div class="panel"><strong>התראות אחרונות</strong></div>
    {''.join(alert_html)}
  </div>
</div>
<p class="note">Guardian קורא את אותו מסד הארכיון. אין תיקון אוטומטי של הסביבה — רק התראה והכוונה למאמר.</p>
{"<p class='note'>שגיאת סריקה: " + html.escape(self.last_scan_error) + "</p>" if self.last_scan_error else ""}
</div></div></body></html>"""
        return page.encode("utf-8")

    def apply_settings(self, form: dict[str, list[str]]) -> str:
        action = (form.get("action") or ["save"])[0]
        if action == "pause":
            self.state["running"] = False
            self.save_config()
            return "הסריקה הושהתה"
        if action == "resume":
            self.state["running"] = True
            self.save_config()
            return "הסריקה חודשה"
        if action == "scan":
            count = self.scan_once()
            return f"נסרקו לוגים · {count} התראות חדשות"
        try:
            interval = max(15, int((form.get("interval") or ["60"])[0]))
        except ValueError:
            interval = 60
        self.state["interval_seconds"] = interval
        enabled_ids = {key.removeprefix("enable_") for key in form if key.startswith("enable_")}
        for target in self.state["targets"]:
            target["enabled"] = target.get("id") in enabled_ids
        extra = ((form.get("extra") or [""])[0] or "").strip()
        if extra and extra not in self.state["extra_paths"]:
            self.state["extra_paths"].append(extra)
        self.save_config()
        return "ההגדרות נשמרו"


def build_guardian_handler(app: GuardianApp):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if urlparse(self.path).path in ("/", "/index.html"):
                body = app.home_page()
                self._send(200, body, "text/html; charset=utf-8")
                return
            self._send(404, "לא נמצא".encode("utf-8"), "text/plain; charset=utf-8")

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/settings":
                self._send(404, b"missing", "text/plain; charset=utf-8")
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            payload = self.rfile.read(length).decode("utf-8", errors="replace")
            form = parse_qs(payload)
            notice = app.apply_settings(form)
            location = "/?notice=" + quote(notice)
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            return

    return Handler


def serve_guardian(
    data_dir: Path,
    *,
    port: int = 8766,
    open_browser: bool = True,
    reader_base: str = "http://127.0.0.1:8765",
) -> None:
    app = GuardianApp(data_dir, reader_base=reader_base)
    app.start_worker()
    server = ThreadingHTTPServer(("127.0.0.1", port), build_guardian_handler(app))
    url = f"http://127.0.0.1:{port}/"
    print(f"guardian {url}", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    finally:
        app.stop()
        server.server_close()
