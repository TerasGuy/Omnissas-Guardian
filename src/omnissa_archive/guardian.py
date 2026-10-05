"""Omnissa Guardian — local log monitoring with archive-backed suggestions."""

from __future__ import annotations

import html
import json
import os
import re
import socket
import sqlite3
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, quote_plus, urlparse

from omnissa_archive.db import connect, init_db
from omnissa_archive.library import LibraryWatcher, assets_root_for, inbox_dir, resolve_default_database
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
        "label": "Agent (user)",
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

# First pass reads the log that is already on disk. Huge files stay bounded to the tail.
FIRST_SCAN_MAX_BYTES = 2 * 1024 * 1024

ERROR_RE = re.compile(
    r"\b(error|exception|failed|failure|fatal|critical|unable to|cannot |warn(?:ing)?)\b",
    re.I,
)
LEVELS = ("FATAL", "ERROR", "WARNING", "DEBUG", "INFO")

# Browser search templates from the earlier desktop client. They are never
# opened during a log scan; only an explicit search does that, and only when
# the operator turned the setting on and the network answers.
DEFAULT_ONLINE_SOURCES = [
    {"name": "Omnissa KB", "url": "https://kb.omnissa.com/s/global-search/{q}"},
    {"name": "Omnissa TechZone", "url": "https://techzone.omnissa.com/search#q={q}"},
    {"name": "Broadcom Support", "url": "https://support.broadcom.com/web/ecx/search#q={q}"},
    {"name": "VMware Community", "url": "https://community.broadcom.com/search?q={q}"},
    {"name": "Reddit r/vmware", "url": "https://www.reddit.com/r/vmware/search/?q={q}"},
    {"name": "Google", "url": "https://www.google.com/search?q=Omnissa+Horizon+{q}"},
]


def network_reachable(host: str = "kb.omnissa.com", port: int = 443, timeout: float = 2.0) -> bool:
    """True when a short TCP connection to the public KB host succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def classify_level(line: str) -> str:
    text = line or ""
    lowered = text.lower()
    if re.search(r"\b(fatal|critical)\b", lowered):
        return "FATAL"
    if re.search(r"\b(error|exception|failed|failure|unable to|cannot )\b", lowered):
        return "ERROR"
    if re.search(r"\bwarn(?:ing)?\b", lowered):
        return "WARNING"
    if re.search(r"\bdebug\b", lowered):
        return "DEBUG"
    if re.search(r"\binfo\b", lowered):
        return "INFO"
    return "ERROR"


def builtin_suggestion(level: str, line: str) -> str:
    snippet = (line or "").strip()
    if len(snippet) > 160:
        snippet = snippet[:157] + "…"
    if level == "FATAL":
        return f"Critical failure detected. Review the component that wrote this line and related Horizon services. ({snippet})"
    if level == "WARNING":
        return f"Warning pattern in logs. Check configuration and recent changes around this message. ({snippet})"
    return f"Error pattern in logs. Search the offline archive for matching KB articles and verify connectivity/auth. ({snippet})"
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
    """Machine status code: empty|pattern|ok|unc|missing."""
    expanded = expand_path(raw)
    if not expanded:
        return "empty"
    path = Path(expanded)
    if any(ch in expanded for ch in "*?"):
        parent = path.parent if path.parent != path else Path(".")
        return "pattern" if parent.exists() else "missing"
    if path.is_file() or path.is_dir():
        return "ok"
    if expanded.startswith("\\\\"):
        return "unc"
    return "missing"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _clean_watch_targets(rows: list) -> list[dict]:
    """Keep every saved watch path, including an empty list after the user removes them all."""
    cleaned: list[dict] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(rows or [], start=1):
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("path") or "").strip()
        if not path:
            continue
        label = str(raw.get("label") or "").strip() or path
        ident = str(raw.get("id") or "").strip() or f"path-{index}"
        if ident in seen_ids:
            ident = f"{ident}-{index}"
        seen_ids.add(ident)
        cleaned.append(
            {
                "id": ident,
                "label": label,
                "path": path,
                "enabled": bool(raw.get("enabled", True)),
            }
        )
    return cleaned


def _merge_extra_paths(targets: list[dict], extras: list) -> list[dict]:
    seen = {item.get("path") for item in targets}
    merged = list(targets)
    for raw in extras or []:
        path = str(raw or "").strip()
        if not path or path in seen:
            continue
        merged.append(
            {
                "id": f"extra-{len(merged) + 1}",
                "label": "Extra path",
                "path": path,
                "enabled": True,
            }
        )
        seen.add(path)
    return merged


class GuardianApp:
    def __init__(self, data_dir: Path, reader_base: str = "http://127.0.0.1:8765") -> None:
        self.data_dir = data_dir
        self.reader_base = reader_base.rstrip("/")
        self.config_path = data_dir / "guardian_config.json"
        self.state = self._load_config()
        self.alerts: list[dict] = []
        self.history: list[dict] = []
        self.system_log: list[dict] = []
        self.offsets: dict[str, int] = {}
        self.last_scan_at = ""
        self.last_scan_error = ""
        self.running = True
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._alert_seq = 0
        inbox_dir(data_dir)
        self.library = LibraryWatcher(data_dir)
        db = resolve_default_database(data_dir)
        self.library.bind(db)
        conn = connect(db)
        init_db(conn)
        conn.close()
        if self.state.get("reader_base"):
            self.reader_base = str(self.state["reader_base"]).rstrip("/")
        self._log_system("Guardian ready")

    def _load_config(self) -> dict:
        if self.config_path.is_file():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        else:
            data = {}
        if isinstance(data.get("targets"), list):
            targets = _clean_watch_targets(data["targets"])
        else:
            targets = [dict(item) for item in DEFAULT_LOG_TARGETS]
        targets = _merge_extra_paths(targets, data.get("extra_paths") or [])
        return {
            "interval_seconds": int(data.get("interval_seconds") or 60),
            "targets": targets,
            "extra_paths": [],
            # Desktop UX: start stopped until the operator clicks Start Monitoring.
            "running": bool(data.get("running", False)),
            "language": "en",
            "reader_base": str(data.get("reader_base") or self.reader_base),
            "online_search": bool(data.get("online_search", False)),
            "online_sources": self._online_sources_from(data.get("online_sources")),
        }

    @staticmethod
    def _online_sources_from(raw) -> list[dict]:
        sources = []
        for item in raw or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            url = str(item.get("url") or "").strip()
            if name and "{q}" in url:
                sources.append({"name": name, "url": url})
        if sources:
            return sources
        return [dict(item) for item in DEFAULT_ONLINE_SOURCES]

    def save_config(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def database_path(self) -> Path:
        current = resolve_default_database(self.data_dir)
        event = self.library.poll(current)
        if event is not None:
            return event.path
        return current

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
                items.append((f"Extra path {index}", raw))
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

    def scan_once(self, *, stop_when_paused: bool = False) -> int:
        found = 0
        try:
            for label, raw in self.enabled_paths():
                if stop_when_paused and not self.state.get("running"):
                    break
                for file_path in self.iter_log_files(raw):
                    if stop_when_paused and not self.state.get("running"):
                        break
                    found += self._scan_file(label, file_path, stop_when_paused=stop_when_paused)
            self.last_scan_at = _utcnow()
            self.last_scan_error = ""
        except OSError as exc:
            self.last_scan_error = str(exc)
        return found

    def _scan_file(self, label: str, path: Path, *, stop_when_paused: bool = False) -> int:
        key = str(path)
        try:
            size = path.stat().st_size
        except OSError:
            return 0
        first = key not in self.offsets
        if first:
            offset = 0 if size <= FIRST_SCAN_MAX_BYTES else size - FIRST_SCAN_MAX_BYTES
        else:
            offset = self.offsets[key]
            if offset > size:
                offset = 0
            if size == offset:
                return 0
        added = 0
        try:
            with path.open("rb") as handle:
                if offset:
                    handle.seek(offset)
                    if first:
                        handle.readline()
                chunk = handle.read().decode("utf-8", errors="replace")
                new_offset = handle.tell()
        except OSError:
            if first:
                self.offsets[key] = size
            return 0
        self.offsets[key] = new_offset
        for line in chunk.splitlines():
            if stop_when_paused and not self.state.get("running"):
                break
            if not ERROR_RE.search(line):
                continue
            alert = self._make_alert(label, path, line.strip())
            with self._lock:
                self.alerts.insert(0, alert)
                self.alerts = self.alerts[:80]
            added += 1
        return added

    def _log_system(self, message: str) -> None:
        entry = {"at": _utcnow(), "message": message}
        with self._lock:
            self.system_log.insert(0, entry)
            self.system_log = self.system_log[:200]

    def language(self) -> str:
        return "en"

    def set_language(self, lang: str) -> str:
        self.state["language"] = "en"
        self.save_config()
        return "en"

    def set_monitoring(self, enabled: bool) -> None:
        self.state["running"] = _as_bool(enabled)
        self.save_config()
        self._log_system("Monitoring started" if self.state["running"] else "Monitoring stopped")

    def clear_alerts(self) -> None:
        with self._lock:
            self.alerts.clear()
        self._log_system("Live detections cleared")

    def severity_counts(self) -> dict[str, int]:
        counts = {level: 0 for level in LEVELS}
        with self._lock:
            for alert in self.alerts:
                level = alert.get("level") or "ERROR"
                if level in counts:
                    counts[level] += 1
        return counts

    def snapshot(self) -> dict:
        with self._lock:
            alerts = list(self.alerts)
            history = list(self.history[:200])
            system = list(self.system_log[:100])
        targets = []
        for target in self.state["targets"]:
            raw = target.get("path") or ""
            targets.append(
                {
                    "id": target.get("id"),
                    "label": target.get("label") or "",
                    "path": raw,
                    "enabled": bool(target.get("enabled")),
                    "status": path_status(raw),
                }
            )
        extras = [
            {"path": raw, "status": path_status(raw)}
            for raw in (self.state.get("extra_paths") or [])
            if raw
        ]
        return {
            "language": self.language(),
            "running": bool(self.state.get("running")),
            "interval_seconds": int(self.state.get("interval_seconds") or 60),
            "reader_base": self.reader_base,
            "database": str(self.database_path()),
            "last_scan_at": self.last_scan_at,
            "last_scan_error": self.last_scan_error,
            "counts": self.severity_counts(),
            "alerts": alerts,
            "history": history,
            "system_log": system,
            "targets": targets,
            "extra_paths": extras,
            "online_search": bool(self.state.get("online_search")),
            "online_sources": list(self.state.get("online_sources") or []),
        }

    def set_online_search(self, enabled: bool) -> None:
        self.state["online_search"] = bool(enabled)

    def prepare_online_search(self, query: str) -> dict:
        """Build online search links. Never called from the log scan.

        Disabled by default. When the setting is on, links are returned only
        if the public KB host accepts a short connection.
        """
        sources = list(self.state.get("online_sources") or [])
        text = (query or "").strip()
        if not self.state.get("online_search"):
            return {"status": "disabled", "urls": [], "sources": sources}
        if not text:
            return {"status": "empty", "urls": [], "sources": sources}
        if not network_reachable():
            return {"status": "offline", "urls": [], "sources": sources}
        encoded = quote_plus(text[:200])
        urls = [
            {"name": source["name"], "url": source["url"].replace("{q}", encoded)}
            for source in sources
            if "{q}" in (source.get("url") or "")
        ]
        return {"status": "ok", "urls": urls, "sources": sources}

    def update_watch_dirs(
        self,
        *,
        enabled_ids: list[str],
        interval: int,
        extra: str = "",
        reader_base: str | None = None,
    ) -> str:
        self.state["interval_seconds"] = max(15, int(interval or 60))
        enabled = set(enabled_ids or [])
        for target in self.state["targets"]:
            target["enabled"] = target.get("id") in enabled
        extra = (extra or "").strip()
        notice = "saved"
        known = {item.get("path") for item in self.state["targets"]}
        if extra and extra not in known:
            self.state["targets"].append(
                {
                    "id": f"extra-{len(self.state['targets']) + 1}",
                    "label": "Extra path",
                    "path": extra,
                    "enabled": True,
                }
            )
            notice = "extra_added"
        if reader_base is not None:
            base = reader_base.strip().rstrip("/")
            if base:
                self.reader_base = base
                self.state["reader_base"] = base
        self.state["extra_paths"] = []
        self.save_config()
        self._log_system("Watch directories / settings updated")
        return notice

    def set_watch_targets(self, rows: list, interval: int) -> str:
        """Replace the watch list. Built-in paths are ordinary rows and can be edited or removed."""
        self.state["targets"] = _clean_watch_targets(list(rows or []))
        self.state["extra_paths"] = []
        self.state["interval_seconds"] = max(15, int(interval or 60))
        self.save_config()
        self._log_system("Watch directories updated")
        return "saved"

    def search_archive(self, query: str, limit: int = 8) -> list[dict]:
        conn = self._conn()
        try:
            return suggest_solutions(conn, query, limit=limit, reader_base=self.reader_base)
        finally:
            conn.close()

    def _make_alert(self, label: str, path: Path, line: str) -> dict:
        level = classify_level(line)
        conn = self._conn()
        try:
            suggestions = suggest_solutions(conn, line, reader_base=self.reader_base)
        finally:
            conn.close()
        self._alert_seq += 1
        alert = {
            "id": self._alert_seq,
            "at": _utcnow(),
            "level": level,
            "label": label,
            "path": str(path),
            "logfile": path.name,
            "line": line[:500],
            "suggestion": builtin_suggestion(level, line),
            "suggestions": suggestions,
            "kb": (suggestions[0]["title"] if suggestions else ""),
            "kb_link": (suggestions[0]["reader_link"] if suggestions else ""),
        }
        with self._lock:
            self.history.insert(0, alert)
            self.history = self.history[:500]
        return alert

    def start_worker(self) -> None:
        def loop() -> None:
            while not self._stop.is_set():
                if self.state.get("running", False):
                    self.scan_once(stop_when_paused=True)
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
        status_text = f"{open_count} alerts" if open_count else "No open alerts"
        scan_text = self.last_scan_at or "not yet"
        body_paths = []
        for target in self.state["targets"]:
            raw = target.get("path") or ""
            checked = " checked" if target.get("enabled") else ""
            status = path_status(raw)
            ident = html.escape(str(target.get("id") or ""))
            body_paths.append(
                '<div class="path-row">'
                f'<input type="checkbox" name="enable_{ident}" value="1"{checked}>'
                "<div>"
                f'<input type="text" name="label_{ident}" value="{html.escape(target.get("label") or "")}">'
                f'<input type="text" name="path_{ident}" value="{html.escape(raw)}">'
                "</div>"
                f'<span class="pill"><span class="dot {"ok" if status == "ok" else "warn"}"></span>{html.escape(status)}</span>'
                f'<label><input type="checkbox" name="remove_{ident}" value="1"> Remove</label>'
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
                    f"<p>{html.escape(top['published_at'] or 'No date')} · {html.escape(top['excerpt'][:180])}</p></div>"
                    f"<a class='btn' href=\"{html.escape(top['reader_link'])}\" target='_blank' rel='noopener'>Open in archive</a>"
                    "</div>"
                )
            else:
                suggest = (
                    "<div class='suggest'><div><h3>No strong match</h3>"
                    "<p>Search the archive manually.</p></div>"
                    f"<a class='ghost' href=\"{html.escape(self.reader_base + '/search?q=' + quote(alert['line'][:80]))}\" target='_blank' rel='noopener'>Search the archive</a></div>"
                )
            alert_html.append(
                f"<div class='alert'><div class='meta'>{html.escape(alert['at'])} · {html.escape(alert['label'])}</div>"
                f"<div class='log'>{html.escape(alert['line'])}</div>{suggest}</div>"
            )
        if not alert_html:
            alert_html.append('<div class="panel"><p class="note">No alerts yet. The scan runs in the background.</p></div>')
        running = self.state.get("running", False)
        page = f"""<!DOCTYPE html>
<html lang="en" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omnissa Guardian</title><style>{PAGE_CSS}</style>
<meta http-equiv="refresh" content="30"></head><body><div class="shell">
<nav class="side">
  <a class="active" href="/">Guardian</a>
  <a href="{html.escape(self.reader_base)}/" target="_blank" rel="noopener">Archive</a>
</nav>
<div class="content">
<h1>Omnissa Guardian</h1>
<p class="sub">Local and UNC log monitoring · alerts · a suggested article from the archive</p>
<div class="panel status-bar">
  <span class="pill"><span class="dot {"ok" if running else "warn"}"></span>{"Scan running" if running else "Scan paused"}</span>
  <span class="pill">Interval: {int(self.state.get("interval_seconds") or 60)} seconds</span>
  <span class="pill">Last scan: {html.escape(scan_text)}</span>
  <span class="pill"><span class="dot {status_dot}"></span>{html.escape(status_text)}</span>
  <span class="pill">Database: {html.escape(self.database_path().name)}</span>
</div>
<div class="grid-2">
  <div class="panel">
    <form method="post" action="/settings">
      <div class="status-bar" style="margin-bottom:8px"><strong>Log locations</strong></div>
      <p class="note">Edit or remove any path, including the ones that come with the program. Add a local path or a UNC path.</p>
      {''.join(body_paths)}
      <div style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <label><span>Scan interval (seconds)</span><input type="number" name="interval" min="15" step="15" value="{int(self.state.get('interval_seconds') or 60)}"></label>
        <label><span>Extra path / UNC</span><input type="text" name="extra" placeholder="\\\\server\\share\\logs or C:\\logs"></label>
      </div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button type="submit" name="action" value="save">Save</button>
        <button type="submit" name="action" value="{"pause" if running else "resume"}">{"Pause" if running else "Resume"}</button>
        <button type="submit" name="action" value="scan">Scan now</button>
      </div>
    </form>
  </div>
  <div>
    <div class="panel"><strong>Recent alerts</strong></div>
    {''.join(alert_html)}
  </div>
</div>
<p class="note">Guardian reads the same archive database. It does not change the environment. It only raises an alert and points to an article.</p>
{"<p class='note'>Scan error: " + html.escape(self.last_scan_error) + "</p>" if self.last_scan_error else ""}
</div></div></body></html>"""
        return page.encode("utf-8")

    def apply_settings(self, form: dict[str, list[str]]) -> str:
        action = (form.get("action") or ["save"])[0]
        if action == "pause":
            self.set_monitoring(False)
            return "Scan paused"
        if action == "resume":
            self.set_monitoring(True)
            return "Scan resumed"
        if action == "scan":
            count = self.scan_once()
            return f"Logs scanned · {count} new alerts"
        try:
            interval = max(15, int((form.get("interval") or ["60"])[0]))
        except ValueError:
            interval = 60
        rows = []
        for target in self.state["targets"]:
            ident = str(target.get("id") or "")
            if form.get(f"remove_{ident}"):
                continue
            label = ((form.get(f"label_{ident}") or [target.get("label") or ""])[0] or "").strip()
            path = ((form.get(f"path_{ident}") or [target.get("path") or ""])[0] or "").strip()
            rows.append(
                {
                    "id": ident,
                    "label": label or path,
                    "path": path,
                    "enabled": bool(form.get(f"enable_{ident}")),
                }
            )
        extra = ((form.get("extra") or [""])[0] or "").strip()
        if extra:
            rows.append({"id": "", "label": "Extra path", "path": extra, "enabled": True})
        self.set_watch_targets(rows, interval)
        return "Settings saved"


def build_guardian_handler(app: GuardianApp):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if urlparse(self.path).path in ("/", "/index.html"):
                body = app.home_page()
                self._send(200, body, "text/html; charset=utf-8")
                return
            self._send(404, b"Not found", "text/plain; charset=utf-8")

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
