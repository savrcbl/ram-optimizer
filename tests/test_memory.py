from types import SimpleNamespace

import memory

GB = 1024 ** 3


def fake_vm(total=16 * GB, available=4 * GB, percent=75.0):
    return lambda: SimpleNamespace(total=total, available=available, percent=percent)


def test_stats_values(monkeypatch):
    monkeypatch.setattr(memory.psutil, "virtual_memory", fake_vm())
    s = memory.get_memory_stats()
    assert s == {"total_gb": 16.0, "used_gb": 12.0, "available_gb": 4.0, "percent": 75.0}


def test_tight_at_and_above_threshold(monkeypatch):
    monkeypatch.setattr(memory.psutil, "virtual_memory", fake_vm(percent=85.0))
    assert memory.is_memory_tight(85) is True
    assert memory.is_memory_tight(90) is False


def test_available_mb(monkeypatch):
    monkeypatch.setattr(memory.psutil, "virtual_memory", fake_vm(available=2 * GB))
    assert memory.get_available_mb() == 2048.0
