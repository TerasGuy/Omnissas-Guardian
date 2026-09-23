from omnissa_archive.urls import (
    canonical_kb,
    canonical_queue_url,
    guide_of,
    is_english_doc,
    kb_article_id,
    locale_of,
)


def test_english_docs_skip_locales_and_disallowed_paths():
    assert is_english_doc("https://docs.omnissa.com/Horizon8InstallUpgrade/SystemRequirements")
    assert not is_english_doc("https://docs.omnissa.com/de-DE/Horizon8InstallUpgrade/SystemRequirements")
    assert not is_english_doc("https://docs.omnissa.com/api/bundles")
    assert not is_english_doc("https://docs.omnissa.com/search?q=horizon")
    assert not is_english_doc("https://docs.omnissa.com/")
    assert locale_of("https://docs.omnissa.com/ja-JP/Guide/Topic") == "ja-JP"
    assert locale_of("https://docs.omnissa.com/Guide/Topic") == "en"


def test_guide_uses_bundle_or_first_segment():
    assert guide_of("https://docs.omnissa.com/Horizon8InstallUpgrade/SystemRequirements") == "Horizon8InstallUpgrade"
    assert guide_of("https://docs.omnissa.com/bundle/Horizon-Security/page/Horizon8LogFiles.html") == "Horizon-Security"
    assert guide_of("https://kb.omnissa.com/s/article/1027744") == "kb"


def test_kb_urls_are_normalized_and_old_path_is_blocked():
    assert kb_article_id("https://kb.vmware.com/s/article/1027744") == "1027744"
    assert canonical_kb("https://kb.omnissa.com/kb/s/article/1017939") == "https://kb.omnissa.com/s/article/1017939"
    assert kb_article_id("https://kb.omnissa.com/articles/1027744") is None
    assert canonical_queue_url("https://kb.vmware.com/s/article/1027744?lang=en") == "https://kb.omnissa.com/s/article/1027744"
    assert (
        canonical_queue_url("https://docs.omnissa.com/Horizon8InstallUpgrade/HorizonConnectionServerRequirements.md")
        == "https://docs.omnissa.com/Horizon8InstallUpgrade/HorizonConnectionServerRequirements"
    )
