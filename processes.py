import logging
import os

import psutil

log = logging.getLogger("ram_optimizer")

PROTECTED: frozenset[str] = frozenset({
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
    "dwm.exe", "explorer.exe", "fontdrvhost.exe", "sihost.exe",
    "taskhostw.exe", "ctfmon.exe", "msmpeng.exe",
    "securityhealthservice.exe", "python.exe", "pythonw.exe",
})


def is_protected(name: str | None, pid: int) -> bool:
    """True for protected names and for our own process."""
    return pid == os.getpid() or (name or "").lower() in PROTECTED


def list_top_processes(limit: int | None = 15) -> list[dict]:
    """Processes sorted by RAM (RSS) descending. limit=None returns all."""
    rows = []
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            info = proc.info
            mem = info.get("memory_info")
            if mem is None:
                continue
            name = info.get("name") or "?"
            rows.append({
                "pid": info["pid"],
                "name": name,
                "memory_mb": round(mem.rss / (1024 * 1024), 1),
                "protected": is_protected(name, info["pid"]),
            })
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    rows.sort(key=lambda r: r["memory_mb"], reverse=True)
    return rows if limit is None else rows[:limit]


def close_process(pid: int) -> tuple[bool, str]:
    """Politely close a process. Refuses protected processes and ourselves."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except psutil.NoSuchProcess:
        return False, "process no longer exists"
    except psutil.AccessDenied:
        return False, "access denied"

    if is_protected(name, pid):
        log.warning("Refused to close protected process %s (pid %s)", name, pid)
        return False, "protected process"

    try:
        proc.terminate()
        try:
            proc.wait(3)
        except psutil.TimeoutExpired:
            log.warning("terminate timed out, killing %s (pid %s)", name, pid)
            proc.kill()
            proc.wait(3)
    except psutil.NoSuchProcess:
        pass  # already gone, which is what we wanted
    except psutil.AccessDenied:
        log.warning("Access denied closing %s (pid %s)", name, pid)
        return False, "access denied"
    except psutil.TimeoutExpired:
        return False, "process did not exit"

    log.info("Closed process %s (pid %s)", name, pid)
    return True, "closed"
