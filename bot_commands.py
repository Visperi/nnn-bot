import logging
from typing import Optional, Tuple
from sqlite3 import IntegrityError
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

from database import DatabaseHandler


logger = logging.getLogger(__name__)
TZ_HELSINKI = ZoneInfo("Europe/Helsinki")


class BotCommands:

    def __init__(self):
        self.db = DatabaseHandler("app.db")

    @staticmethod
    def format_time(days: int, hours: int, minutes: int, seconds: int) -> str:
        substrings = []
        if days > 0:
            substrings.append(f"{days} päivää")
        if hours > 0:
            substrings.append(f"{hours} tuntia")
        if minutes > 0:
            substrings.append(f"{minutes} minuuttia")
        substrings.append(f"{seconds} sekuntia")

        return ", ".join(substrings)

    @staticmethod
    def calculate_time_diff(minuend: datetime, subtrahend: datetime) -> Tuple[int, int, int, int]:
        """
        Calculate difference between two datetimes.

        :param minuend: The minuend, i.e. where the second datetime is subtracted from.
        :param subtrahend: Subtrahend, i.e. datetime that is subtracted from the first datetime.
        :return: The difference as tuple of (days, hours, minutes, seconds).
        """
        diff = minuend - subtrahend
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return diff.days, hours, minutes, seconds

    def get_time_left(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get how much time there is left of NNN.

        :return: Time left as tuple (days, hours, minutes, seconds), or None if NNN has not started.
        """
        current_time = datetime.now(TZ_HELSINKI)
        nnn_end = datetime(current_time.year, 12, 1, tzinfo=TZ_HELSINKI)

        if nnn_end < current_time:
            return None

        return self.calculate_time_diff(nnn_end, current_time)

    def get_time_gone(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get how long the NNN has been on.

        :return: Time left as tuple (days, hours, minutes, seconds), or None if the NNN has already ended.
        """
        current_time = datetime.now(TZ_HELSINKI)
        nnn_start = datetime(current_time.year, 11, 1, tzinfo=TZ_HELSINKI)

        if nnn_start > current_time:
            return None

        return self.calculate_time_diff(current_time, nnn_start)

    async def time_left_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        time_left = self.get_time_left()
        if not time_left:
            await update.effective_chat.send_message("Ohi on!")
            return

        time_left_str = self.format_time(*time_left)
        await update.effective_chat.send_message(f"NNN:ää jäljellä:\n\n{time_left_str}")

    async def lost_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        time_gone = self.get_time_gone()
        if not time_gone:
            await update.effective_chat.send_message("NNN ei ole käynnissä.")
            return

        time_gone_str = self.format_time(*time_gone)
        user = update.effective_user
        if user.username:
            username = f"@{user.username}"
        else:
            username = update.effective_user.first_name

        try:
            self.db.add(user.id, datetime.now(TZ_HELSINKI))
        except IntegrityError:
            await update.effective_chat.send_message(f"{username} on jo hävinnyt.")
            return

        try:
            await update.effective_chat.set_administrator_custom_title(user.id, "loser")
        except Exception as e:
            logger.error("Error at setting custom title:", exc_info=e)

        await update.effective_chat.send_message(f"{username} kesti {time_gone_str} ja hävisi.")

    async def statistics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # TODO: Implement this
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Komento ei tee vielä mitään.")
