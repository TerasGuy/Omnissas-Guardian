"""Hebrew / English UI strings for Omnissa Guardian desktop."""

from __future__ import annotations

SUPPORTED = ("he", "en")
DEFAULT_LANG = "he"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Omnissa Guardian Ultimate",
        "brand": "OMNISSA GUARDIAN ULTIMATE",
        "subtitle": "Proactive VDI Log Monitoring & Troubleshooting",
        "version": "v2.0.0",
        "lang_he": "עברית",
        "lang_en": "English",
        "fatal": "FATAL",
        "error": "ERROR",
        "warning": "WARNING",
        "debug": "DEBUG",
        "info": "INFO",
        "no_detections": "No detections yet.",
        "detections_count": "{n} detections",
        "status_stopped": "STOPPED – configure directories then click Start Monitoring",
        "status_running": "RUNNING – scanning log directories every {sec}s",
        "status_paused": "PAUSED – monitoring is paused",
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
        "detail_hint": "DETAIL (double-click a row) – shows built-in suggestion + top offline KB matches.",
        "open_archive": "Open in Archive",
        "no_match": "No strong archive match",
        "no_match_hint": "Search the offline archive manually.",
        "watch_title": "Watch directories",
        "watch_help": "Defaults from KB 1027744. Add a local path or UNC share.",
        "extra_path": "Extra path / UNC",
        "add_path": "Add path",
        "path_status": "Status",
        "enabled": "Enabled",
        "interval": "Scan interval (seconds)",
        "save": "Save",
        "scan_now": "Scan now",
        "kb_title": "KB / Archive source",
        "kb_db": "Active database",
        "kb_open_reader": "Open Archive Reader",
        "kb_search_placeholder": "Search archive…",
        "settings_title": "Settings",
        "settings_lang": "Interface language",
        "settings_interval": "Default scan interval",
        "settings_reader": "Archive reader URL",
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
        "scan_done": "Scan finished · {n} new detections",
        "cleared": "Detections cleared",
        "extra_added": "Path added",
    },
    "he": {
        "app_title": "Omnissa Guardian Ultimate",
        "brand": "OMNISSA GUARDIAN ULTIMATE",
        "subtitle": "ניטור לוגים יזום ופתרון תקלות VDI",
        "version": "v2.0.0",
        "lang_he": "עברית",
        "lang_en": "English",
        "fatal": "FATAL",
        "error": "ERROR",
        "warning": "WARNING",
        "debug": "DEBUG",
        "info": "INFO",
        "no_detections": "אין זיהויים עדיין.",
        "detections_count": "{n} זיהויים",
        "status_stopped": "עצור – הגדירו תיקיות ואז לחצו על התחלת ניטור",
        "status_running": "פועל – סורק תיקיות לוג כל {sec} שניות",
        "status_paused": "מושהה – הניטור מושהה",
        "start_monitoring": "התחלת ניטור",
        "stop_monitoring": "עצירת ניטור",
        "tab_live": "ניטור חי",
        "tab_history": "היסטוריה",
        "tab_watch": "תיקיות מעקב",
        "tab_kb": "מקורות KB",
        "tab_settings": "הגדרות",
        "tab_email": "דוא״ל",
        "tab_system": "יומן מערכת",
        "realtime": "זיהויים בזמן אמת",
        "filter": "סינון:",
        "clear": "ניקוי",
        "search_kb": "חיפוש ב־KB",
        "col_timestamp": "זמן",
        "col_level": "רמה",
        "col_logfile": "קובץ לוג",
        "col_message": "הודעה",
        "col_suggestion": "הצעה",
        "col_kb": "KB",
        "detail_hint": "פירוט (לחיצה כפולה על שורה) – הצעה מובנית + התאמות KB אופליין.",
        "open_archive": "פתח בארכיון",
        "no_match": "לא נמצאה התאמה חזקה",
        "no_match_hint": "אפשר לחפש ידנית בארכיון האופליין.",
        "watch_title": "תיקיות מעקב",
        "watch_help": "ברירות מחדל לפי KB 1027744. אפשר להוסיף נתיב מקומי או UNC.",
        "extra_path": "נתיב נוסף / UNC",
        "add_path": "הוספת נתיב",
        "path_status": "סטטוס",
        "enabled": "פעיל",
        "interval": "מרווח סריקה (שניות)",
        "save": "שמירה",
        "scan_now": "סריקה עכשיו",
        "kb_title": "מקור KB / ארכיון",
        "kb_db": "מסד פעיל",
        "kb_open_reader": "פתיחת קורא הארכיון",
        "kb_search_placeholder": "חיפוש בארכיון…",
        "settings_title": "הגדרות",
        "settings_lang": "שפת ממשק",
        "settings_interval": "מרווח סריקה ברירת מחדל",
        "settings_reader": "כתובת קורא הארכיון",
        "email_title": "התראות בדוא״ל",
        "email_stub": "שליחת דוא״ל אינה מופעלת בגרסה זו. הזיהויים נשארים במחשב זה.",
        "system_title": "יומן מערכת",
        "system_empty": "אין הודעות מערכת עדיין.",
        "history_title": "היסטוריית זיהויים",
        "history_empty": "ההיסטוריה ריקה.",
        "detail_title": "פירוט זיהוי",
        "built_in": "הצעה מובנית",
        "kb_matches": "התאמות KB אופליין",
        "close": "סגור",
        "path_ok": "נגיש",
        "path_missing": "חסר",
        "path_unc": "UNC",
        "path_pattern": "תבנית",
        "path_empty": "ריק",
        "saved": "ההגדרות נשמרו",
        "scan_done": "הסריקה הסתיימה · {n} זיהויים חדשים",
        "cleared": "הזיהויים נוקו",
        "extra_added": "הנתיב נוסף",
    },
}


def normalize_lang(lang: str | None) -> str:
    value = (lang or DEFAULT_LANG).strip().lower()
    if value.startswith("he"):
        return "he"
    if value.startswith("en"):
        return "en"
    return DEFAULT_LANG


def t(lang: str, key: str, **kwargs: object) -> str:
    code = normalize_lang(lang)
    template = STRINGS[code].get(key) or STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template


def missing_keys() -> dict[str, list[str]]:
    """Return keys present in one language but not the other."""
    he = set(STRINGS["he"])
    en = set(STRINGS["en"])
    return {
        "missing_in_he": sorted(en - he),
        "missing_in_en": sorted(he - en),
    }
