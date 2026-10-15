import logging

try:
    import winreg
except ImportError:  # not on Windows
    winreg = None

log = logging.getLogger("ram_optimizer")

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_KEY = (r"Software\Microsoft\Windows\CurrentVersion"
                r"\Explorer\StartupApproved\Run")

ENABLED_BYTES = b"\x02" + b"\x00" * 11
DISABLED_BYTES = b"\x03" + b"\x00" * 11


def _need_winreg() -> None:
    if winreg is None:
        raise OSError("Startup manager is only supported on Windows")


def _read_run_entries() -> dict[str, str]:
    """name -> command for HKCU Run entries."""
    _need_winreg()
    entries = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                except OSError:
                    break
                entries[name] = str(value)
                i += 1
    except FileNotFoundError:
        pass
    return entries


def _read_approved(name: str) -> bytes | None:
    """Raw StartupApproved bytes for an entry, or None if not set."""
    _need_winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
            data, _ = winreg.QueryValueEx(key, name)
            return bytes(data)
    except FileNotFoundError:
        return None


def _write_approved(name: str, data: bytes) -> None:
    """Write StartupApproved bytes (creates the key if missing)."""
    _need_winreg()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, data)


def _is_enabled(data: bytes | None) -> bool:
    """Windows uses an odd first byte (3, 7) for disabled, even (2, 6) for enabled."""
    return not data or data[0] % 2 == 0


def list_startup_apps() -> list[dict]:
    """Startup apps from HKCU Run with name, command and enabled flag."""
    apps = []
    for name, command in _read_run_entries().items():
        apps.append({"name": name, "command": command,
                     "enabled": _is_enabled(_read_approved(name))})
    return sorted(apps, key=lambda a: a["name"].lower())


def set_startup_enabled(name: str, enabled: bool) -> bool:
    """Enable/disable a startup app. Only flips the StartupApproved byte."""
    try:
        if name not in _read_run_entries():
            return False
        _write_approved(name, ENABLED_BYTES if enabled else DISABLED_BYTES)
    except OSError as e:
        log.error("Could not change startup entry %s: %s", name, e)
        return False
    log.info("Startup app %s %s", name, "enabled" if enabled else "disabled")
    return True
