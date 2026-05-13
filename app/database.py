from collections.abc import Generator
from typing import Any

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from .config import Settings, get_settings

DatabaseConnection = PooledMySQLConnection | MySQLConnectionAbstract


def create_db_connection(settings: Settings) -> DatabaseConnection:
    return mysql.connector.connect(
        host=settings.mysql_server,
        database=settings.mysql_database,
        user=settings.mysql_username,
        password=settings.mysql_password,
    )


def get_db() -> Generator[DatabaseConnection, Any, None]:
    db = create_db_connection(get_settings())
    try:
        yield db
    finally:
        db.close()
