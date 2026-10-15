"""Helpers for the 'never trim' app list.

Names are stored exactly as typed (lowercase, trimmed). Matching ignores a trailing
'.exe', so 'game' and 'game.exe' both protect game.exe.
"""


def normalize(name: str) -> str:
    """Lowercase and trim. Does NOT add or remove anything else."""
    return name.strip().lower()


def match_key(name: str) -> str:
    """Name used for comparing: normalized, without a trailing '.exe'."""
    n = normalize(name)
    return n[:-4] if n.endswith(".exe") else n


def add_excluded(cfg: dict, name: str) -> bool:
    """Add an app to cfg['excluded_apps']. False if empty or already there."""
    n = normalize(name)
    if not n or match_key(n) in {match_key(x) for x in cfg["excluded_apps"]}:
        return False
    cfg["excluded_apps"].append(n)
    cfg["excluded_apps"].sort()
    return True


def remove_excluded(cfg: dict, name: str) -> bool:
    """Remove an app from the list. False if it was not there."""
    key = match_key(name)
    kept = [x for x in cfg["excluded_apps"] if match_key(x) != key]
    removed = len(kept) != len(cfg["excluded_apps"])
    cfg["excluded_apps"][:] = kept
    return removed


def excluded_set(names) -> set[str]:
    """Set of match keys for fast, case-insensitive lookups."""
    return {match_key(n) for n in (names or ())}
