"""English UI strings for Omnissa Guardian desktop."""

from __future__ import annotations

SUPPORTED = ("en",)
DEFAULT_LANG = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Omnissa Guardian Ultimate",
        "brand": "OMNISSA GUARDIAN ULTIMATE",
        "subtitle": "Proactive VDI Log Monitoring & Troubleshooting",
        "version": "v2.0.0",
        "fatal": "FATAL",
        "error": "ERROR",
        "warning": "WARNING",
        "debug": "DEBUG",
        "info": "INFO",
        "no_detections": "No detections yet.",
        "detections_count": "{n} detections",
        "status_stopped": "STOPPED - configure directories then click Start Monitoring",
        "status_running": "RUNNING - scanning log directories every {sec}s",
        "status_paused": "PAUSED - monitoring is paused",
        "start_monitoring": "START MONITORING",
        "stop_monitoring": "STOP MONITORING",
        "tab_live": "Live Monitor",
        "tab_history": "History",
        "tab_watch": "Watch Dirs",
        "tab_kb": "KB Sources",
        "tab_settings": "Settings",
        "tab_email": "Email",
        "tab_system": "System Logs",
        "realtime": "Real-Time Detections",
        "filter": "Filter:",
        "clear": "Clear",
        "search_kb": "Search KB",
        "col_timestamp": "Timestamp",
        "col_level": "Level",
        "col_logfile": "Log File",
        "col_message": "Message",
        "col_suggestion": "Suggestion",
        "col_kb": "KB",
        "detail_hint": "DETAIL (double-click a row) â€“ shows built-in suggestion + top offline KB matches.",
        "open_archive": "Open in Archive",
        "no_match": "No strong archive match",
        "no_match_hint": "Search the offline archive manually.",
        "watch_title": "Watch directories",
        "watch_help": "Use the pencil to edit a path and the trash icon to remove it, including paths that come with the program.",
        "edit_path": "Edit",
        "extra_path": "Extra path / UNC",
        "path_name": "Name",
        "path_location": "Path",
        "remove_path": "Remove",
        "add_path": "Add path",
        "path_status": "Status",
        "enabled": "Enabled",
        "interval": "Scan interval (seconds)",
        "save": "Save",
        "scan_now": "Scan now",
        "kb_title": "KB / Archive source",
        "kb_db": "Active database",
        "kb_open_reader": "Open Archive Reader",
        "kb_search_placeholder": "Search archiveâ€¦",
        "online_title": "Online documents",
        "online_help": "Shown here, and used only when the setting is on and the network can reach the public KB.",
        "online_search_btn": "Search online",
        "online_disabled": "Online search is off. Turn it on in Settings.",
        "online_offline": "No network to the public KB. Staying on the local archive.",
        "online_empty": "Enter a search phrase first.",
        "online_opened": "Opened {n} online searches.",
        "settings_title": "Settings",
        "settings_interval": "Default scan interval",
        "settings_reader": "Archive reader URL",
        "settings_online": "Search online documents",
        "settings_online_hint": "Off by default. A log scan never opens these sites. A search uses them only when this is checked and the network allows it.",
        "email_title": "Email alerts",
        "email_stub": "Email delivery is not enabled in this build. Detections stay on this machine.",
        "system_title": "System log",
        "system_empty": "No system messages yet.",
        "history_title": "Detection history",
        "history_empty": "History is empty.",
        "detail_title": "Detection detail",
        "built_in": "Built-in suggestion",
        "kb_matches": "Offline KB matches",
        "close": "Close",
        "path_ok": "OK",
        "path_missing": "Missing",
        "path_unc": "UNC",
        "path_pattern": "Pattern",
        "path_empty": "Empty",
        "saved": "Settings saved",
        "scan_done": "Scan finished Â· {n} new detections",
        "cleared": "Detections cleared",
        "extra_added": "Path added",
    },
}


def normalize_lang(lang: str | None) -> str:
    return "en"


def t(lang: str, key: str, **kwargs: object) -> str:
    template = STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template

