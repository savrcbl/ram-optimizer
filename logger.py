import logging
from logging.handlers import RotatingFileHandler

from config import get_config_dir


def get_logger(name: str = "ram_optimizer") -> logging.Logger:
    """Return the app logger; writes ram_optimizer.log in the config folder (1 MB rotation)."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        try:
            log_dir = get_config_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                log_dir / "ram_optimizer.log",
                maxBytes=1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
        except OSError:
            handler = logging.StreamHandler()  # fall back to console
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)

    return logger
