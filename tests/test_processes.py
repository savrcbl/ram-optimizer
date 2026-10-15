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
