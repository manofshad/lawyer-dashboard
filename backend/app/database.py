from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection, connect
from psycopg.rows import dict_row

from .settings import Settings


class DatabaseConfigError(RuntimeError):
    pass


class DatabaseConnectionError(RuntimeError):
    pass


def get_database_url(settings: Settings) -> str:
    database_url = settings.database_url.strip()
    if not database_url:
        raise DatabaseConfigError("Database URL is not configured.")
    return database_url


@contextmanager
def get_db_connection(database_url: str) -> Iterator[Connection]:
    try:
        connection = connect(database_url, row_factory=dict_row)
    except Exception as exc:
        raise DatabaseConnectionError("Unable to connect to the database.") from exc

    with connection:
        yield connection
