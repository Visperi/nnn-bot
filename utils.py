import logging
from typing import Tuple
from datetime import datetime
from zoneinfo import ZoneInfo


TZ_HELSINKI = ZoneInfo("Europe/Helsinki")


class LostUser:

    def __init__(self, data: Tuple):
        self._id = data[0]
        self._channel_id = data[1]
        self._username = data[2]
        self._time_lost = data[3]

    @property
    def id(self) -> int:
        return self._id

    @property
    def username(self) -> str:
        return self._username

    @property
    def time_lost(self) -> datetime:
        return datetime.fromtimestamp(self._time_lost, TZ_HELSINKI)


class LogFormatter(logging.Formatter):
    """
    A custom log formatter with log level specific colours.
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    output_format = "[{asctime}] [{levelname}] {name}: {message}"

    LEVEL_COLOURS = (
        (logging.DEBUG, grey),
        (logging.INFO, grey),
        (logging.WARNING, yellow),
        (logging.ERROR, red),
        (logging.CRITICAL, bold_red)
    )

    FORMATTERS = {}
    for level, colour in LEVEL_COLOURS:
        FORMATTERS[level] = logging.Formatter(fmt=colour+output_format+reset, datefmt="%Y-%m-%d %H:%M:%S", style="{")

    def format(self, record) -> str:
        formatter = self.FORMATTERS.get(record.levelno)
        return formatter.format(record)


def configure_logging():
    """
    Configure logging. Sets logging level to logging.WARNING for httpx
    (library used for API requests by the Telegram library.)
    """

    handler = logging.StreamHandler()
    root_logger = logging.getLogger()

    handler.setFormatter(LogFormatter())
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Ignore Telegram library logging in smaller level than warnings
    logging.getLogger("httpx").setLevel(logging.WARNING)
