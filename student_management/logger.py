"""Application logging setup."""
import logging
from .config import LOG_PATH, ensure_directories


def get_logger(name: str = "student_management") -> logging.Logger:
    """Return a configured logger; avoid duplicate handlers on repeated calls."""
    ensure_directories()
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)
    return logger
