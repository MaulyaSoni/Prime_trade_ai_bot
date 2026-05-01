import logging
import os
from datetime import datetime


def setup_logging() -> logging.Logger:
    """
    Sets up structured logging to both a timestamped log file and the console.
    File logs at DEBUG level (verbose), console logs at INFO level (clean).
    """
    os.makedirs("logs", exist_ok=True)
    log_filename = f"logs/trading_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("trading_bot")

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — full debug output
    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # Console handler — info and above only
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"Logging initialised -> {log_filename}")
    return logger