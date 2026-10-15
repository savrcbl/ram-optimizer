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
}


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
    cfg = dict(DEFAULT_CONFIG)  # always a fresh copy
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
            cfg[key] = data[key]
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
