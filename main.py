import logging

from telegram import Update
from telegram.ext import Application, CommandHandler

import utils
from bot_commands import BotCommands


logger = logging.getLogger(__name__)


def start_bot(bot_token: str):
    application = Application.builder().token(bot_token).build()

    commands = BotCommands()
    application.add_handler(CommandHandler("jaljella", commands.time_left_command))
    application.add_handler(CommandHandler("havisin", commands.lost_command))
    application.add_handler(CommandHandler("tilastot", commands.statistics_command))
    application.add_handler(CommandHandler("sijoitukset", commands.placements_command))
    application.add_handler(CommandHandler("status", commands.status_command))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    with open("token.txt", "r") as token_file:
        token = token_file.read().strip()

    utils.configure_logging()
    start_bot(token)
