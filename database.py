import sqlite3
import logging
from datetime import datetime


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
            CREATE TABLE IF NOT EXISTS losers (
                user_id INTEGER PRIMARY KEY,
                timestamp INTEGER NOT NULL
            );
            """)

    def add(self, user_id: int, timestamp: datetime):
        """
        Add user NNN loser data to database.

        :param user_id: Telegram user ID.
        :param timestamp: Timestamp when the user lost.
        :raises IntegrityError: If the user has already lost.
        """
        timestamp = int(timestamp.timestamp())  # Ignore microseconds

        with self.connection:
            self.cursor.execute(
                """
                INSERT INTO losers (user_id, timestamp)
                VALUES 
                    (?, ?)
                """, (user_id, timestamp)
            )

    def get_losers(self):
        """
        Get chat users that have lost.

        :return: List of users that have lost.
        """
        with self.connection:
            losers = self.cursor.execute(
                """
                SELECT user_id, timestamp FROM losers
                """
            ).fetchall()

        return losers


if __name__ == '__main__':
    db = DatabaseHandler("app.db")
    print(db.get_losers())
