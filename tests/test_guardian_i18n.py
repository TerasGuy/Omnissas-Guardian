from omnissa_archive.guardian import builtin_suggestion, classify_level
from omnissa_archive.guardian_i18n import STRINGS, normalize_lang, t


def test_watch_rows_use_icon_buttons():
    from omnissa_archive.guardian_desktop import DESKTOP_HTML

    assert "icon-btn" in DESKTOP_HTML
    assert "WATCH_ICONS" in DESKTOP_HTML
    assert ">Remove</button>" not in DESKTOP_HTML
    assert 'class="modal-bar"' in DESKTOP_HTML
    header = DESKTOP_HTML.split('class="modal-body"')[0]
    assert 'id="btn-close"' in header
    assert 'id="btn-detail-online"' in header


def test_ui_is_english_only():
    assert set(STRINGS) == {"en"}
    assert "עברית" not in "".join(STRINGS["en"].values())
    assert len(STRINGS["en"]) >= 40


def test_normalize_lang_and_translate():
    assert normalize_lang("HE") == "en"
    assert normalize_lang("en-US") == "en"
    assert normalize_lang("xx") == "en"
    assert "MONITORING" in t("en", "start_monitoring").upper()
    assert "60" in t("he", "status_running", sec=60)


def test_classify_level_and_builtin_suggestion():
    assert classify_level("FATAL broker crash") == "FATAL"
    assert classify_level("ERROR LDAP timeout") == "ERROR"
    assert classify_level("WARNING disk almost full") == "WARNING"
    assert "Critical" in builtin_suggestion("FATAL", "FATAL boom")
    assert "Error" in builtin_suggestion("ERROR", "ERROR boom")
