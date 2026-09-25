from omnissa_archive.guardian import builtin_suggestion, classify_level
from omnissa_archive.guardian_i18n import STRINGS, missing_keys, normalize_lang, t


def test_language_dictionaries_have_identical_keys():
    gaps = missing_keys()
    assert gaps["missing_in_he"] == []
    assert gaps["missing_in_en"] == []
    assert set(STRINGS["he"]) == set(STRINGS["en"])
    assert len(STRINGS["he"]) >= 40


def test_normalize_lang_and_translate():
    assert normalize_lang("HE") == "he"
    assert normalize_lang("en-US") == "en"
    assert normalize_lang("xx") == "he"
    assert "START" in t("en", "start_monitoring").upper() or "MONITORING" in t(
        "en", "start_monitoring"
    ).upper()
    assert t("he", "start_monitoring")
    assert "60" in t("en", "status_running", sec=60)


def test_classify_level_and_builtin_suggestion():
    assert classify_level("FATAL broker crash") == "FATAL"
    assert classify_level("ERROR LDAP timeout") == "ERROR"
    assert classify_level("WARNING disk almost full") == "WARNING"
    assert "Critical" in builtin_suggestion("FATAL", "FATAL boom")
    assert "Error" in builtin_suggestion("ERROR", "ERROR boom")
