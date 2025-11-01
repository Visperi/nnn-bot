from typing import Optional, Tuple
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes


def calculate_time_left() -> Optional[Tuple[int, int, int, int]]:
    current_time = datetime.now()
    nnn_end = datetime(current_time.year, 12, 1)

    if nnn_end < current_time:
        return None

    diff = nnn_end - current_time
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return diff.days, hours, minutes, seconds


def calculate_time_gone() -> Optional[Tuple[int, int, int, int]]:
    current_time = datetime.now()
    nnn_start = datetime(current_time.year, 11, 1)

    if nnn_start > current_time:
        return None

    diff = current_time - nnn_start
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return diff.days, hours, minutes, seconds


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


async def time_left_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_left = calculate_time_left()
    if not time_left:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ohi on!")
        return

    time_left_str = format_time(*time_left)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"NNN:ää jäljellä:\n\n{time_left_str}")


async def lost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    time_gone = calculate_time_gone()
    if not time_gone:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="NNN ei ole käynnissä.")
        return

    time_gone_str = format_time(*time_gone)
    username = update.effective_user.username
    if username:
        username = f"@{username}"
    else:
        username = update.effective_user.first_name

    msg = f"{username} kesti {time_gone_str} ja hävisi."
    await context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg)
