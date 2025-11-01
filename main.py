from typing import Optional, Tuple
from datetime import datetime
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="[{asctime}] [{levelname}] {name}: {message}", level=logging.INFO, style="{"
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def calculate_time_left() -> Optional[Tuple[int, int, int, int]]:
    current_time = datetime.now()
    nnn_end = datetime(datetime.now().year, 12, 1)

    if nnn_end < current_time:
        return None

    diff = nnn_end - current_time
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return diff.days, hours, minutes, seconds


async def time_left_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_left = calculate_time_left()
    if not time_left:
        await update.message.reply_text("Ohi on!")
        return

    days, hours, minutes, seconds = time_left

    left_substrings = []
    if days > 0:
        left_substrings.append(f"{days} päivää")
    if hours > 0:
        left_substrings.append(f"{hours} tuntia")
    if minutes > 0:
        left_substrings.append(f"{minutes} minuuttia")

    left_substrings.append(f"{seconds} sekuntia")

    time_left_str = ", ".join(left_substrings)
    await update.message.reply_text(f"NNN:ää jäljellä:\n\n{time_left_str}")


def start_bot(bot_token: str):
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("jaljella", time_left_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    with open("token.txt", "r") as token_file:
        token = token_file.read()
    start_bot(token)
