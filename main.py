import sys

from config import load_config
from logger import get_logger


def main() -> None:
    log = get_logger()
    if sys.platform != "win32":
        print("RAM Optimizer targets Windows. Trimming and startup features will not work here.")
    cfg = load_config()
    log.info("RAM Optimizer starting")
    from gui import App  # imported late so the logger is configured first
    App(cfg).mainloop()
    log.info("RAM Optimizer closed")


if __name__ == "__main__":
    main()
