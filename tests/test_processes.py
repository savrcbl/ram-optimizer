import os
from types import SimpleNamespace

import psutil
import pytest

import processes

MB = 1024 * 1024


class FakeIterProc:
    def __init__(self, pid, name, mb):
        self.info = {"pid": pid, "name": name, "memory_info": SimpleNamespace(rss=mb * MB)}


def test_sorted_descending_and_limit(monkeypatch):
    procs = [FakeIterProc(1, "a.exe", 10), FakeIterProc(2, "b.exe", 300), FakeIterProc(3, "c.exe", 50)]
    monkeypatch.setattr(processes.psutil, "process_iter", lambda attrs: iter(procs))
    rows = processes.list_top_processes(limit=2)
    assert [r["pid"] for r in rows] == [2, 3]


def test_protected_flag(monkeypatch):
    procs = [FakeIterProc(4, "Explorer.EXE", 100), FakeIterProc(5, "chrome.exe", 90)]
    monkeypatch.setattr(processes.psutil, "process_iter", lambda attrs: iter(procs))
    rows = {r["name"]: r["protected"] for r in processes.list_top_processes()}
    assert rows == {"Explorer.EXE": True, "chrome.exe": False}


def test_skips_missing_memory_info(monkeypatch):
    bad = SimpleNamespace(info={"pid": 9, "name": "x", "memory_info": None})
    monkeypatch.setattr(processes.psutil, "process_iter", lambda attrs: iter([bad]))
    assert processes.list_top_processes() == []


class FakeProc:
    terminated = False

    def __init__(self, pid, name="chrome.exe"):
        self._name = name

    def name(self):
        return self._name

    def terminate(self):
        FakeProc.terminated = True

    def wait(self, timeout):
        return 0

    def kill(self):
        raise AssertionError("kill should not be called")


@pytest.fixture(autouse=True)
def reset():
    FakeProc.terminated = False


def test_refuses_protected(monkeypatch):
    monkeypatch.setattr(processes.psutil, "Process", lambda pid: FakeProc(pid, "lsass.exe"))
    ok, reason = processes.close_process(1234)
    assert ok is False and reason == "protected process"
    assert FakeProc.terminated is False


def test_refuses_self(monkeypatch):
    monkeypatch.setattr(processes.psutil, "Process", lambda pid: FakeProc(pid, "foo.exe"))
    ok, _ = processes.close_process(os.getpid())
    assert ok is False and FakeProc.terminated is False


def test_closes_normal_process(monkeypatch):
    monkeypatch.setattr(processes.psutil, "Process", lambda pid: FakeProc(pid))
    assert processes.close_process(99999) == (True, "closed")
    assert FakeProc.terminated is True


def test_missing_process(monkeypatch):
    def boom(pid):
        raise psutil.NoSuchProcess(pid)
    monkeypatch.setattr(processes.psutil, "Process", boom)
    assert processes.close_process(1)[0] is False


def sample_rows():
    return [
        {"pid": 10, "name": "brave.exe", "memory_mb": 400.0, "protected": False},
        {"pid": 11, "name": "Brave.exe", "memory_mb": 300.0, "protected": False},
        {"pid": 120, "name": "code.exe", "memory_mb": 250.0, "protected": False},
        {"pid": 13, "name": "explorer.exe", "memory_mb": 200.0, "protected": True},
    ]


def test_filter_by_name_is_case_insensitive():
    rows, total = processes.filter_processes(sample_rows(), "BRAVE", limit=15)
    assert [r["pid"] for r in rows] == [10, 11] and total == 2


def test_filter_by_pid():
    rows, total = processes.filter_processes(sample_rows(), "120", limit=15)
    assert [r["name"] for r in rows] == ["code.exe"] and total == 1


def test_limit_applies_after_filter_and_total_is_full_match_count():
    rows, total = processes.filter_processes(sample_rows(), "", limit=2)
    assert [r["pid"] for r in rows] == [10, 11] and total == 4


def test_limit_zero_or_none_shows_all():
    assert len(processes.filter_processes(sample_rows(), "", limit=0)[0]) == 4
    assert len(processes.filter_processes(sample_rows(), "", limit=None)[0]) == 4


def test_no_match_gives_empty():
    assert processes.filter_processes(sample_rows(), "zzz") == ([], 0)
