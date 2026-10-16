import json
import logging
import os
from pathlib import Path

log = logging.getLogger("ram_optimizer")

DEFAULT_CONFIG = {
    "trim_threshold_percent": 85,
    "auto_mode": False,
    "check_interval_seconds": 10,
    "cooldown_seconds": 120,
    "min_process_mb_to_trim": 50,
    "excluded_apps": [],
    "process_list_limit": 15,  # 0 = show all
    "close_to_tray": True,
}


def _defaults() -> dict:
    """Fresh copy of the defaults (lists copied too, so callers can't alter them)."""
    return {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_CONFIG.items()}


def get_config_dir() -> Path:
    """Return %APPDATA%/RamOptimizer (falls back to ~/AppData/Roaming)."""
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "RamOptimizer"


def get_config_path() -> Path:
    """Return the full path of config.json."""
    return get_config_dir() / "config.json"


def load_config() -> dict:
    """Load settings; missing or broken file gives defaults. Never writes."""
    cfg = _defaults()
    try:
        with open(get_config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return cfg
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not read config, using defaults: %s", e)
        return cfg

    if not isinstance(data, dict):
        log.warning("Config file is not a JSON object, using defaults")
        return cfg

    for key, default in DEFAULT_CONFIG.items():
        if key in data and type(data[key]) is type(default):
            value = data[key]
            if isinstance(default, list):
                value = [x for x in value if isinstance(x, str)]
            cfg[key] = value
    return cfg


def save_config(cfg: dict) -> None:
    """Save settings, creating the folder if needed."""
    path = get_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        os.replace(tmp, path)
    except OSError as e:
        log.error("Could not save config to %s: %s", path, e)
