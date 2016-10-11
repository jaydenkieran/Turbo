import sys
import logging
import colorlog

from .main import Turbo

__all__ = ['Turbo']

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(
    filename='turbo.log', encoding='utf-8', mode='w')
fh.setFormatter(logging.Formatter(
    "[{asctime}] {levelname} ({filename} L{lineno}, {funcName}): {message}", style='{'
))
sh = logging.StreamHandler(stream=sys.stdout)
sh.setFormatter(colorlog.LevelFormatter(
    fmt={
        "DEBUG": "{log_color}{levelname} ({module} L{lineno}, {funcName}): {message}",
        "INFO": "{log_color}{message}",
        "WARNING": "{log_color}{levelname}: {message}",
        "ERROR": "{log_color}{levelname} ({module} L{lineno}, {funcName}): {message}",
        "CRITICAL": "{log_color}{levelname} ({module} L{lineno}, {funcName}): {message}"
    },
    log_colors={
        "DEBUG": "purple",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red"
    },
    style='{'
))
sh.setLevel(logging.DEBUG)

logger.addHandler(fh)
logger.addHandler(sh)
