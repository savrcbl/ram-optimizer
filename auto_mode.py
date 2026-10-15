import logging
import threading
import time

from config import load_config
from memory import is_memory_tight
from trimmer import smart_trim

log = logging.getLogger("ram_optimizer")


class AutoWatcher:
    """Background thread that trims memory when RAM is tight."""

    def __init__(self, get_config=load_config, is_tight=is_memory_tight,
                 trim=smart_trim, on_trim=None, clock=time.monotonic):
        self._get_config = get_config
        self._is_tight = is_tight
        self._trim = trim
        self._on_trim = on_trim
        self._clock = clock
        self._last_trim: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start watching (does nothing if already running)."""
        if self.is_running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("Auto mode started")

    def stop(self) -> None:
        """Stop watching and wait for the thread to end."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None
        log.info("Auto mode stopped")

    def _tick(self) -> dict | None:
        """One check. Trims if tight and cooldown passed. Returns result or None."""
        cfg = self._get_config()
        now = self._clock()
        if (self._last_trim is not None
                and now - self._last_trim < cfg["cooldown_seconds"]):
            return None
        if not self._is_tight(cfg["trim_threshold_percent"]):
            return None
        result = self._trim(cfg["min_process_mb_to_trim"])
        self._last_trim = self._clock()
        if self._on_trim:
            self._on_trim(result)
        return result

    def _run(self) -> None:
        while not self._stop.is_set():
            interval = 10
            try:
                self._tick()
                interval = max(1, self._get_config()["check_interval_seconds"])
            except Exception:
                log.exception("Auto mode error")
            self._stop.wait(interval)
