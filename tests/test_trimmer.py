import os

import trimmer


def row(pid, name, mb, protected=False):
    return {"pid": pid, "name": name, "memory_mb": mb, "protected": protected}


sleeps: list = []


def setup_fakes(monkeypatch, rows, foreground=None):
    calls = []
    sleeps.clear()
    monkeypatch.setattr(trimmer, "list_top_processes", lambda limit=None: rows)
    monkeypatch.setattr(trimmer, "get_foreground_pid", lambda: foreground)
    monkeypatch.setattr(trimmer, "get_memory_stats", lambda: {"percent": 80.0})
    avail = iter([4000.0, 5500.0])
    monkeypatch.setattr(trimmer, "get_available_mb", lambda: next(avail))
    monkeypatch.setattr(trimmer.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(trimmer, "trim_process", lambda pid: calls.append(pid) or 20.0)
    return calls


def test_skips_protected_small_foreground_and_self(monkeypatch):
    rows = [
        row(1, "lsass.exe", 500, protected=True),
        row(2, "tiny.exe", 10),
        row(3, "front.exe", 400),
        row(os.getpid(), "me.exe", 400),
        row(4, "chrome.exe", 300),
    ]
    calls = setup_fakes(monkeypatch, rows, foreground=3)
    result = trimmer.smart_trim(min_process_mb=50)
    assert calls == [4]
    assert result["processes_trimmed"] == 1
    assert result["mb_freed"] == 1500.0  # real system change, not 20 MB x processes
    assert sleeps == [2.0]


def test_summary_has_all_keys(monkeypatch):
    setup_fakes(monkeypatch, [])
    result = trimmer.smart_trim()
    assert set(result) == {"processes_trimmed", "mb_freed", "before_percent", "after_percent"}


def test_trim_process_returns_zero_off_windows():
    if trimmer.sys.platform != "win32":
        assert trimmer.trim_process(1) == 0.0
