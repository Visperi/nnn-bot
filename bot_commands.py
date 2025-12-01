import logging
import statistics
import io
from typing import Optional, Tuple, List
from sqlite3 import IntegrityError
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from telegram import Update, Chat

from database import DatabaseHandler
from utils import TZ_HELSINKI

logger = logging.getLogger(__name__)
current_year = datetime.now(TZ_HELSINKI).year
NNN_START = datetime(current_year, 11, 1, tzinfo=TZ_HELSINKI)
NNN_END = datetime(current_year, 12, 1, tzinfo=TZ_HELSINKI)


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


def calculate_time_diff(minuend: datetime, subtrahend: datetime) -> Tuple[int, int, int, int]:
    """
    Calculate difference between two datetime objects.

    :param minuend: The minuend, i.e. where the second datetime is subtracted from.
    :param subtrahend: Subtrahend, i.e. datetime that is subtracted from the first datetime.
    :return: The difference as tuple of (days, hours, minutes, seconds).
    """
    diff = minuend - subtrahend
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return diff.days, hours, minutes, seconds


def get_time_left() -> Optional[Tuple[int, int, int, int]]:
    """
    Calculate how much time there is left of NNN.

    :return: Time left as tuple (days, hours, minutes, seconds), or None if NNN has not started.
    """
    current_time = datetime.now(TZ_HELSINKI)

    if NNN_END < current_time:
        return None

    return calculate_time_diff(NNN_END, current_time)


def get_time_gone() -> Optional[Tuple[int, int, int, int]]:
    """
    Calculate how long the NNN has been on.

    :return: Time left as tuple (days, hours, minutes, seconds), or None if the NNN has already ended.
    """
    current_time = datetime.now(TZ_HELSINKI)

    if NNN_START > current_time:
        return None

    return calculate_time_diff(current_time, NNN_START)


def calculate_average_time(lose_times: List[datetime]) -> Optional[Tuple[int, int, int, int]]:
    """
    Calculate an average between datetime objects.

    :param lose_times: List of datetime objects.
    :return: Average time between datetime objects as tuple (days, hours, minutes, seconds), or None if the list is
             empty.
    """
    if len(lose_times) == 0:
        return None

    avg = statistics.mean((dt.timestamp() for dt in lose_times))
    avg_dt = datetime.fromtimestamp(avg, TZ_HELSINKI)
    return calculate_time_diff(avg_dt, NNN_START)


class BotCommands:

    def __init__(self, promote_lost_users: bool, lost_user_title: Optional[str]):
        if promote_lost_users and not lost_user_title:
            raise ValueError("Lost user title must be a non-empty string")
        if len(lost_user_title) > 16:
            raise ValueError("Admin title cannot be longer than 16 characters")

        self.promote_lost_users = promote_lost_users
        self.lost_user_title = lost_user_title
        self.db = DatabaseHandler("app.db")

    @staticmethod
    async def promote_chat_user(update: Update, user_id: int, title: str):
        await update.effective_chat.promote_member(user_id, can_pin_messages=True)
        await update.effective_chat.set_administrator_custom_title(user_id, title)

    @staticmethod
    async def time_left_command(update: Update, _):
        time_left = get_time_left()
        if not time_left:
            await update.effective_chat.send_message("Ohi on!")
            return

        time_left_str = format_time(*time_left)
        await update.effective_chat.send_message(f"NNN:ää jäljellä:\n\n{time_left_str}")

    async def lost_command(self, update: Update, _):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        time_gone = get_time_gone()
        if not time_gone:
            await update.effective_chat.send_message("NNN ei ole käynnissä.")
            return

        time_gone_str = format_time(*time_gone)
        user = update.effective_user

        try:
            self.db.add(user.id, update.effective_chat.id, user.name, datetime.now(TZ_HELSINKI))
        except IntegrityError:
            await update.effective_chat.send_message(f"{user.name} on jo hävinnyt.")
            return

        message = f"{user.name} kesti {time_gone_str} ja hävisi."

        if self.promote_lost_users:
            try:
                await self.promote_chat_user(update, user.id, self.lost_user_title)
            except Exception as e:
                if str(e) == "Can't remove chat owner":
                    message += "\n\nOlet kanavan omistaja eikä titteliäsi voi muokata."
                elif str(e) == "Bots can't add new chat members":
                    message += "\n\nEsiinnyt anonyyminä eikä titteliäsi voi muokata."
                else:
                    logger.error("Error at setting custom title:", exc_info=e)

        await update.effective_chat.send_message(message)

    async def statistics_command(self, update: Update, _):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        num_users = await update.effective_chat.get_member_count() - 1  # Subtract the bot from calculations
        lost_users = self.db.get_lost_users(update.effective_chat.id)
        num_lost_users = len(lost_users)
        lost_percentage = round(num_lost_users / num_users * 100, 1)
        avg_lost = calculate_average_time([user.time_lost for user in lost_users])
        if not avg_lost:
            formatted_avg_lost = "Ei laskettavissa"
        else:
            formatted_avg_lost = format_time(*avg_lost)

        if get_time_left() is None:
            users_left_label = "Selvinneitä"
        else:
            users_left_label = "Yhä mukana"

        msg = (f"Kanavan {update.effective_chat.effective_name} NNN-tilastot\n\n"
               f"Hävinneitä: {num_lost_users} ({lost_percentage} %)\n"
               f"{users_left_label}: {num_users - num_lost_users}\n\n"
               f"Häviäjät selvisivät keskimäärin: {formatted_avg_lost}")
        await update.effective_chat.send_message(msg)


    async def placements_command(self, update: Update, _):
        lost_users = self.db.get_lost_users(update.effective_chat.id)
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return
        if not lost_users:
            await update.effective_chat.send_message("Yksikään kanavan jäsenistä ei ole vielä hävinnyt.")
            return

        lost_users.sort(key=lambda x: x.time_lost)
        placements = ""
        for i, user in enumerate(lost_users):
            diff = calculate_time_diff(user.time_lost, NNN_START)
            placements += f"{i+1}. {user.username.lstrip('@')}\t({format_time(*diff)})\n"

        await update.effective_chat.send_message(f"Näin vähän aikaa kanavan coomerit kesti:\n\n{placements}")


    async def status_command(self, update: Update, _):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        tg_user = update.effective_user
        tg_chat = update.effective_chat
        lost_user = self.db.get_lost_user(tg_user.id, tg_chat.id)
        if not lost_user:
            time_gone = get_time_gone()
            diff_days = (time_gone[0] * 24 + time_gone[1]) / 24
            await tg_chat.send_message(f"{tg_user.name} on kestänyt "
                                       f"jo {round(diff_days, 1)} vuorokautta! Hullu tyyppi.")
        else:
            diff = calculate_time_diff(lost_user.time_lost, NNN_START)
            formatted = format_time(*diff)
            msg = f"{tg_user.name} kesti NNN:ää yhteensä: {formatted}."
            await tg_chat.send_message(msg)

            if tg_user.name != lost_user.username:
                self.db.update_username(tg_user.id, tg_chat.id, tg_user.name)

    async def distribution_days_command(self, update: Update, _):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        lost_users = self.db.get_lost_users(update.effective_chat.id)
        if not lost_users:
            await update.effective_chat.send_message("Yksikään kanavan käyttäjistä ei ole vielä hävinnyt.")
            return

        data = {}
        for user in lost_users:
            key = user.time_lost.strftime("%d.%m.")
            data.setdefault(key, 0)
            data[key] += 1

        dates_lost = list(data.keys())
        num_lost = list(data.values())

        plt.bar(dates_lost, num_lost)
        plt.title("Hävinneet päivämäärien suhteen")
        plt.xlabel("Päivämäärä [dd.mm.]")
        plt.ylabel("Hävinneiden määrä")
        plt.xticks(rotation=90)
        plt.subplots_adjust(bottom=0.18)

        # Plot trend line if enough lost users
        if len(dates_lost) > 2:
            x_coords = list(range(1, len(dates_lost) + 1))
            z = np.polyfit(x_coords, num_lost, 2)
            p = np.poly1d(z)
            plt.plot(dates_lost, p(x_coords), linestyle="--", color="red")

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        await update.effective_chat.send_photo(buffer)

    async def distribution_hours_command(self, update: Update, _):
        if update.effective_chat.type == Chat.PRIVATE:
            await update.effective_chat.send_message("Komento toimii vain kanavilla.")
            return

        lost_users = self.db.get_lost_users(update.effective_chat.id)
        if not lost_users:
            await update.effective_chat.send_message("Yksikään kanavan käyttäjistä ei ole vielä hävinnyt.")
            return

        data = {}
        for user in lost_users:
            key = user.time_lost.hour
            data.setdefault(key, 0)
            data[key] += 1

        hours_lost = list(data.keys())
        num_lost = list(data.values())

        plt.bar(hours_lost, num_lost)
        plt.title("Hävinneet kellonajan suhteen")
        plt.xlabel("Kellonaika tunteina")
        plt.ylabel("Hävinneiden määrä")
        plt.xticks(list(range(24)), [f"{hour:02d}" for hour in range(24)])

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        await update.effective_chat.send_photo(buffer)

    @staticmethod
    async def help_command(update: Update, _):
        commands = [
            "/jaljella - Kertoo kauanko NNN:ää on jäljellä.",
            "/havisin - Ilmoita hävinneesi NNN:n tältä vuodelta.",
            "/tilastot - Näyttää tilastoja kanavan NNN-osallistujista.",
            "/sijoitukset - Näyttää listan kanavan hävinneistä käyttäjistä.",
            "/jakauma - Piirtää kuvaajan häviäjien määristä päivämäärien suhteen.",
            "/jakauma2 - Piirtää kuvaajan häviäjien määristä kellonajan suhteen."
            "/status - Näyttää oman NNN-statuksesi.",
            "/help - Lähettää tämän viestin yksityisviestillä."
        ]

        joined = "\n".join(commands)
        help_message = f"Botin kaikki komennot:\n\n{joined}"
        await update.effective_user.send_message(help_message)

        if update.effective_chat.type != Chat.PRIVATE:
            await update.effective_message.reply_text("Ohjeet lähetetty yksityisviestillä.")
