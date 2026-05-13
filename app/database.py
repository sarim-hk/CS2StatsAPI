from collections.abc import Generator, Sequence
from typing import Any, Protocol, cast

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from .config import Settings, get_settings

QueryParams = Sequence[Any] | dict[str, Any] | None


class DatabaseCursor(Protocol):
    def execute(self, operation: str, params: QueryParams = None) -> Any: ...
    def fetchone(self) -> dict[str, Any] | None: ...
    def fetchall(self) -> list[dict[str, Any]]: ...
    def close(self) -> Any: ...
    def __enter__(self) -> "DatabaseCursor": ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...


class DatabaseConnection(Protocol):
    def cursor(self, *args: Any, **kwargs: Any) -> DatabaseCursor: ...
    def close(self) -> Any: ...


def create_db_connection(settings: Settings) -> DatabaseConnection:
    connection: PooledMySQLConnection | MySQLConnectionAbstract = mysql.connector.connect(
        host=settings.mysql_server,
        database=settings.mysql_database,
        user=settings.mysql_username,
        password=settings.mysql_password,
    )
    return cast(DatabaseConnection, connection)


def get_db() -> Generator[DatabaseConnection, Any, None]:
    db = create_db_connection(get_settings())
    try:
        yield db
    finally:
        db.close()
