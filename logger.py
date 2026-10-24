"""Logging setup: technical messages go to logs/mnc.log (the screen stays clean).

Usage in any file:
    from logger import get_logger
    log = get_logger("employees")
    log.info("...")   log.warning("...")   log.error("...")   log.exception("...")
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).with_name("logs")
_ready = False


def get_logger(name):
    global _ready
    if not _ready:
        LOG_DIR.mkdir(exist_ok=True)
        # rotating file: when it reaches ~500 KB it starts a new one (keeps 3 old ones)
        handler = RotatingFileHandler(LOG_DIR / "mnc.log", maxBytes=500_000,
                                      backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        root = logging.getLogger("mnc")
        root.setLevel(logging.INFO)
        root.addHandler(handler)
        _ready = True
    return logging.getLogger("mnc." + name)
