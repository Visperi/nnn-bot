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


def configure_logging():
    logging.basicConfig(
        format="[{asctime}] [{levelname}] {name}: {message}",
        level=logging.INFO,
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
