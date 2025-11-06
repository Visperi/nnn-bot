import logging
import tomllib

from telegram import Update
from telegram.ext import Application, CommandHandler

import utils
from bot_commands import BotCommands


logger = logging.getLogger(__name__)


def start_bot(bot_token: str, promote_lost_users: bool, lost_user_title: str = None):
    application = Application.builder().token(bot_token).build()

    commands = BotCommands(promote_lost_users, lost_user_title)
    application.add_handler(CommandHandler("jaljella", commands.time_left_command))
    application.add_handler(CommandHandler("havisin", commands.lost_command))
    application.add_handler(CommandHandler("tilastot", commands.statistics_command))
    application.add_handler(CommandHandler("sijoitukset", commands.placements_command))
    application.add_handler(CommandHandler("status", commands.status_command))
    application.add_handler(CommandHandler("help", commands.help_command))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    with open("config.toml", "rb") as config_file:
        config = tomllib.load(config_file)

    token = config["bot_token"]
    lost_users = config["lost_users"]

    utils.configure_logging()
    start_bot(token, lost_users["promote_lost_users"], lost_users["lost_user_title"])
