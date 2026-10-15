import startup


def fake_registry(monkeypatch, entries, approved=None):
    store = dict(approved or {})
    monkeypatch.setattr(startup, "_read_run_entries", lambda: dict(entries))
    monkeypatch.setattr(startup, "_read_approved", lambda name: store.get(name))
    monkeypatch.setattr(startup, "_write_approved", lambda name, data: store.__setitem__(name, data))
    return store


def test_list_enabled_state(monkeypatch):
    fake_registry(
        monkeypatch,
        {"Discord": "d.exe", "Steam": "s.exe", "OneDrive": "o.exe", "Zoom": "z.exe"},
        {"Steam": b"\x03" + b"\x00" * 11, "OneDrive": b"\x02" + b"\x00" * 11,
         "Zoom": b"\x07" + b"\x00" * 11},
    )
    state = {a["name"]: a["enabled"] for a in startup.list_startup_apps()}
    assert state == {"Discord": True, "Steam": False, "OneDrive": True, "Zoom": False}


def test_disable_writes_03_then_enable_writes_02(monkeypatch):
    store = fake_registry(monkeypatch, {"Discord": "d.exe"})
    assert startup.set_startup_enabled("Discord", False) is True
    assert store["Discord"][0] == 0x03 and len(store["Discord"]) == 12
    assert startup.set_startup_enabled("Discord", True) is True
    assert store["Discord"][0] == 0x02


def test_unknown_name_is_rejected(monkeypatch):
    store = fake_registry(monkeypatch, {"Discord": "d.exe"})
    assert startup.set_startup_enabled("Nope", False) is False
    assert store == {}


def test_off_windows_fails_cleanly():
    if startup.winreg is None:
        assert startup.set_startup_enabled("x", False) is False
