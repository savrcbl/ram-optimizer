import ctypes
import logging
import os
import sys
import time

import psutil

from memory import get_available_mb, get_memory_stats
from processes import list_top_processes

log = logging.getLogger("ram_optimizer")

PROCESS_SET_QUOTA = 0x0100
PROCESS_QUERY_INFORMATION = 0x0400


def _winapi():
    """Load kernel32/psapi with correct signatures (Windows only)."""
    if sys.platform != "win32":
        raise OSError("Memory trimming is only supported on Windows")
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
    psapi.EmptyWorkingSet.restype = wintypes.BOOL
    return kernel32, psapi


def get_foreground_pid() -> int | None:
    """PID owning the window the user is looking at, or None."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value or None
    except OSError:
        return None


def trim_process(pid: int) -> float:
    """Trim one process's working set. Returns MB freed (0 on any failure)."""
    try:
        kernel32, psapi = _winapi()
        proc = psutil.Process(pid)
        before = proc.memory_info().rss
        handle = kernel32.OpenProcess(
            PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle:
            return 0.0
        try:
            psapi.EmptyWorkingSet(handle)
        finally:
            kernel32.CloseHandle(handle)
        after = proc.memory_info().rss
        return max(0.0, (before - after) / (1024 * 1024))
    except (OSError, psutil.Error):
        return 0.0


def smart_trim(min_process_mb: int = 50, settle_seconds: float = 2.0) -> dict:
    """Trim big, non-protected, non-foreground processes. Returns a summary.

    mb_freed is the real change in system available memory, measured after a short
    settle delay. It is NOT the sum of per-process drops (shared memory would be
    counted several times).
    """
    before_pct = get_memory_stats()["percent"]
    before_mb = get_available_mb()
    foreground = get_foreground_pid()
    trimmed = 0
    for p in list_top_processes(limit=None):
        if p["protected"] or p["pid"] == foreground or p["pid"] == os.getpid():
            continue
        if p["memory_mb"] < min_process_mb:
            continue
        if trim_process(p["pid"]) > 0:
            trimmed += 1
    time.sleep(settle_seconds)  # let Windows finish moving pages
    after_pct = get_memory_stats()["percent"]
    freed = max(0.0, get_available_mb() - before_mb)
    result = {
        "processes_trimmed": trimmed,
        "mb_freed": round(freed, 1),
        "before_percent": before_pct,
        "after_percent": after_pct,
    }
    log.info("Smart trim: %d processes, %.0f MB freed (system), RAM %.1f%% -> %.1f%%",
             trimmed, freed, before_pct, after_pct)
    return result
