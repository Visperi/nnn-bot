import sqlite3
import logging
from datetime import datetime
from typing import List, Tuple

from utils import LostUser


logger = logging.getLogger(__name__)


class DatabaseHandler:
    """
    A database handler for NNN losers.
    """

    def __init__(self, db_path: str):
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self.create_table_if_not_exists()
        logger.info(f"Database connected to file {db_path}.")

    def create_table_if_not_exists(self):
        """
        Create the database and losers table they do not exist.
        """
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users_lost (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                PRIMARY KEY (user_id, chat_id)
            );
            """)

    def add(self, user_id: int, chat_id: int, username: str, timestamp: datetime):
        """
        Add user NNN loser data to database.

        :param user_id: Telegram user ID.
        :param chat_id: Telegram chat ID.
        :param username: Telegram user username.
        :param timestamp: Datetime of when the user lost.
        :raises IntegrityError: If the user has already lost.
        """
        timestamp = int(timestamp.timestamp())  # Ignore microseconds

        with self.connection:
            self.cursor.execute(
                """
                INSERT INTO users_lost (user_id, chat_id, username, timestamp)
                VALUES 
                    (?, ?, ?, ?)
                """, (user_id, chat_id, username, timestamp)
            )

    def get_losers(self, chat_id: int) -> List[LostUser]:
        """
        Get chat users that have lost.

        :param chat_id: Telegram chat ID.
        :return: Users that have lost in the channel as a list of LostUser objects.
        """
        with self.connection:
            losers = self.cursor.execute(
                """
                SELECT * FROM users_lost WHERE chat_id = ?
                """, (chat_id, )
            ).fetchall()

        return [LostUser(attrs) for attrs in losers]
