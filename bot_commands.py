import logging
from typing import Optional, Tuple
from sqlite3 import IntegrityError
from datetime import datetime

from telegram import Update, Chat
from telegram.ext import ContextTypes

from database import DatabaseHandler
from utils import TZ_HELSINKI

logger = logging.getLogger(__name__)
current_year = datetime.now(TZ_HELSINKI).year
NNN_START = datetime(current_year, 11, 1, tzinfo=TZ_HELSINKI)
NNN_END= datetime(current_year, 12, 1, tzinfo=TZ_HELSINKI)


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

        if NNN_END < current_time:
            return None

        return self.calculate_time_diff(NNN_END, current_time)

    def get_time_gone(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get how long the NNN has been on.

        :return: Time left as tuple (days, hours, minutes, seconds), or None if the NNN has already ended.
        """
        current_time = datetime.now(TZ_HELSINKI)

        if NNN_START > current_time:
            return None

        return self.calculate_time_diff(current_time, NNN_START)

    async def time_left_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        time_left = self.get_time_left()
        if not time_left:
            await update.effective_chat.send_message("Ohi on!")
            return

        time_left_str = self.format_time(*time_left)
        await update.effective_chat.send_message(f"NNN:ää jäljellä:\n\n{time_left_str}")

    async def lost_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        time_gone = self.get_time_gone()
        if not time_gone:
            await update.effective_chat.send_message("NNN ei ole käynnissä.")
            return

        time_gone_str = self.format_time(*time_gone)
        user = update.effective_user

        try:
            self.db.add(user.id, update.effective_chat.id, user.name, datetime.now(TZ_HELSINKI))
        except IntegrityError:
            await update.effective_chat.send_message(f"{user.name} on jo hävinnyt.")
            return

        message = f"{user.name} kesti {time_gone_str} ja hävisi."
        try:
            await update.effective_chat.promote_member(user.id)
            await update.effective_chat.set_administrator_custom_title(user.id, "coomer")
        except Exception as e:
            if str(e) == "Can't remove chat owner":
                message += "\n\nOlet kanavan omistaja eikä titteliäsi voi muokata."
            elif str(e) == "Bots can't add new chat members":
                message += "\n\nEsiinnyt anonyyminä eikä titteliäsi voi muokata."
            else:
                logger.error("Error at setting custom title:", exc_info=e)

        await update.effective_chat.send_message(message)

    async def statistics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        num_users = await update.effective_chat.get_member_count()
        lost_users = self.db.get_losers(update.effective_chat.id)
        num_lost_users = len(lost_users)

        msg = (f"Kanavan {update.effective_chat.effective_name} NNN-tilastot\n\n"
               f"Hävinneitä: {num_lost_users}\n"
               f"Yhä mukana: {num_users - num_lost_users}")
        await update.effective_chat.send_message(msg)


    async def placements_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        lost_users = self.db.get_losers(update.effective_chat.id)
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return
        if not lost_users:
            await update.effective_chat.send_message("Yksikään kanavan jäsenistä ei ole vielä hävinnyt.")
            return

        lost_users.sort(key=lambda x: x.time_lost)
        placements = ""
        for i, user in enumerate(lost_users):
            diff = self.calculate_time_diff(user.time_lost, NNN_START)
            placements += f"{i+1}. {user.username.lstrip('@')}\t({self.format_time(*diff)})\n"

        await update.effective_chat.send_message(f"Näin vähän aikaa kanavan coomerit kesti:\n\n{placements}")


    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        tg_user = update.effective_user
        tg_chat = update.effective_chat
        lost_user = self.db.get_lost_user(tg_user.id, tg_chat.id)
        if not lost_user:
            time_gone = self.get_time_gone()
            diff_days = (time_gone[0] * 24 + time_gone[1]) / 24
            await tg_chat.send_message(f"{tg_user.name} on kestänyt "
                                       f"jo {round(diff_days, 1)} vuorokautta! Hullu tyyppi.")
        else:
            diff = self.calculate_time_diff(lost_user.time_lost, NNN_START)
            formatted = self.format_time(*diff)
            msg = f"{tg_user.name} kesti NNN:ää yhteensä: {formatted}."
            await tg_chat.send_message(msg)

            if tg_user.name != lost_user.username:
                self.db.update_username(tg_user.id, tg_chat.id, tg_user.name)

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        commands = [
            "/jaljella - Kertoo kauanko NNN:ää on jäljellä.",
            "/havisin - Ilmoita hävinneesi NNN:n tältä vuodelta.",
            "/tilastot - Näyttää tilastoja kanavan NNN-osallistujista.",
            "/sijoitukset - Näyttää listan kanavan hävinneistä käyttäjistä.",
            "/status - Näyttää oman NNN-statuksesi.",
            "/help - Lähettää tämän viestin yksityisviestillä."
        ]

        joined = "\n".join(commands)
        help_message = f"Botin kaikki komennot:\n\n{joined}"
        await update.effective_user.send_message(help_message)

        if update.effective_chat.type != Chat.PRIVATE:
            await update.effective_message.reply_text("Ohjeet lähetetty yksityisviestillä.")
