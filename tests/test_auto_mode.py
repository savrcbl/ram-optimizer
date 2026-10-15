import time

from auto_mode import AutoWatcher

CFG = {"excluded_apps": ["game.exe"], "trim_threshold_percent": 85, "cooldown_seconds": 100,
       "min_process_mb_to_trim": 50, "check_interval_seconds": 1}


seen: list = []


def make(tight=True, results=None):
    seen.clear()
    now = {"t": 0.0}
    results = results if results is not None else []
    w = AutoWatcher(
        get_config=lambda: CFG,
        is_tight=lambda pct: tight,
        trim=lambda mb, excluded=None: seen.append(excluded) or {"processes_trimmed": 1, "mb_freed": 5.0,
                         "before_percent": 90, "after_percent": 85},
        on_trim=results.append,
        clock=lambda: now["t"],
    )
    return w, now, results


def test_trims_when_tight():
    w, _, results = make(tight=True)
    assert w._tick() is not None
    assert len(results) == 1


def test_no_trim_when_not_tight():
    w, _, results = make(tight=False)
    assert w._tick() is None and results == []


def test_cooldown_respected():
    w, now, results = make()
    w._tick()
    now["t"] = 50
    assert w._tick() is None
    now["t"] = 101
    assert w._tick() is not None
    assert len(results) == 2


def test_starts_and_stops_cleanly():
    w, _, _ = make(tight=False)
    w.start()
    assert w.is_running
    t0 = time.time()
    w.stop()
    assert not w.is_running
    assert time.time() - t0 < 2


def test_exclude_list_is_passed_to_trim():
    w, _, _ = make()
    w._tick()
    assert seen == [["game.exe"]]
