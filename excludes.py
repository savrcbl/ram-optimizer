"""Helpers for the 'never trim' app list. Names are stored lowercase, e.g. 'chrome.exe'."""


def normalize(name: str) -> str:
    """Lowercase, trim spaces, and add .exe when no extension was typed."""
    n = name.strip().lower()
    if n and "." not in n:
        n += ".exe"
    return n


def add_excluded(cfg: dict, name: str) -> bool:
    """Add an app to cfg['excluded_apps']. False if empty or already there."""
    n = normalize(name)
    if not n or n in cfg["excluded_apps"]:
        return False
    cfg["excluded_apps"].append(n)
    cfg["excluded_apps"].sort()
    return True


def remove_excluded(cfg: dict, name: str) -> bool:
    """Remove an app from the list. False if it was not there."""
    n = normalize(name)
    if n not in cfg["excluded_apps"]:
        return False
    cfg["excluded_apps"].remove(n)
    return True


def excluded_set(names) -> set[str]:
    """Lowercase set for fast, case-insensitive lookups."""
    return {n.lower() for n in (names or ())}
