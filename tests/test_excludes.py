import excludes


def cfg():
    return {"excluded_apps": []}


def test_normalize_does_not_add_exe():
    assert excludes.normalize("  Game  ") == "game"
    assert excludes.normalize("OBS64.EXE") == "obs64.exe"
    assert excludes.normalize("   ") == ""


def test_add_and_duplicate():
    c = cfg()
    assert excludes.add_excluded(c, "Game") is True
    assert excludes.add_excluded(c, "game.exe") is False  # same app, .exe ignored
    assert c["excluded_apps"] == ["game"]


def test_empty_name_rejected():
    assert excludes.add_excluded(cfg(), "  ") is False


def test_list_is_kept_sorted():
    c = cfg()
    excludes.add_excluded(c, "zoom.exe")
    excludes.add_excluded(c, "chrome.exe")
    assert c["excluded_apps"] == ["chrome.exe", "zoom.exe"]


def test_remove():
    c = cfg()
    excludes.add_excluded(c, "game.exe")
    assert excludes.remove_excluded(c, "GAME.exe") is True  # matches 'game' too
    assert excludes.remove_excluded(c, "game") is False
    assert c["excluded_apps"] == []


def test_excluded_set_is_case_insensitive():
    assert excludes.excluded_set(["Game.EXE", "obs"]) == {"game", "obs"}
    assert excludes.excluded_set(None) == set()
