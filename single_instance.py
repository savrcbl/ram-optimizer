"""Stop a second copy from starting (two trays, two auto-trimmers, one config file)."""
import ctypes
import sys

ERROR_ALREADY_EXISTS = 183
_handle = None  # keep a reference so the mutex lives as long as the process


def acquire() -> bool:
    """True if we are the only running instance. Always True off Windows."""
    global _handle
    if sys.platform != "win32":
        return True
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    _handle = kernel32.CreateMutexW(None, False, "Local\\RamOptimizerSingleInstance")
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def tell_already_running() -> None:
    """Show a message box (the exe has no console, so print would go nowhere)."""
    text = ("RAM Optimizer is already running.\n"
            "Look for its icon in the system tray, near the clock.")
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, text, "RAM Optimizer", 0x40)
    else:
        print(text)
