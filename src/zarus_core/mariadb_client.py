"""MariaDB client wrapper for zarus_core package."""

from __future__ import annotations

from typing import Any, cast

from .exceptions import MariaDBClientError
from .logger import CustomLogging

try:
    import mysql.connector as _mysql_connector
except ImportError:
    _mysql_connector = None


class MariaDBClient:
    """Simple MariaDB client with reconnect support and helper methods."""

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        reconnect_attempts: int = 5,
        reconnect_delay: int = 2,
    ):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._logger = CustomLogging(component_name="MariaDBClient").get_logger()

        if _mysql_connector is None:
            raise MariaDBClientError(
                "mysql-connector-python is required to use MariaDBClient. "
                "Install it with: pip install mysql-connector-python"
            )

        self._logger.info(f"Connecting to MariaDB at {host} as {user}")
        self.conn = _mysql_connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
        )
        self.cursor = self.conn.cursor()
        self._logger.info("MariaDB connection established")

    @classmethod
    def from_json(cls, config_data: dict[str, Any]) -> "MariaDBClient":
        db_conf = config_data.get("mariadb", {})
        return cls(
            host=db_conf.get("host", "localhost"),
            user=db_conf.get("user", ""),
            password=db_conf.get("password", ""),
            database=db_conf.get("database", ""),
            reconnect_attempts=(
                db_conf.get("reconnect_attempts")
                if db_conf.get("reconnect_attempts") is not None
                else db_conf.get("reconnectAttempts", 5)
            ),
            reconnect_delay=(
                db_conf.get("reconnect_delay")
                if db_conf.get("reconnect_delay") is not None
                else db_conf.get("reconnectDelay", 2)
            ),
        )

    def ensure_connection(self) -> None:
        if not self.conn.is_connected():
            self._logger.warning("MariaDB connection lost. Attempting to reconnect")
            self.conn.reconnect(
                attempts=self.reconnect_attempts,
                delay=self.reconnect_delay,
            )
            self.cursor = self.conn.cursor()
            self._logger.info("Reconnected to MariaDB")

    def execute(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
        commit: bool = False,
    ) -> None:
        self.ensure_connection()
        self.cursor.execute(query, params or ())
        if commit:
            self.conn.commit()

    def fetchone(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
    ) -> tuple[Any, ...] | None:
        self.execute(query, params=params, commit=False)
        return cast(tuple[Any, ...] | None, self.cursor.fetchone())

    def fetchall(
        self,
        query: str,
        params: tuple[Any, ...] | None = None,
    ) -> list[tuple[Any, ...]]:
        self.execute(query, params=params, commit=False)
        return cast(list[tuple[Any, ...]], self.cursor.fetchall())

    def close(self) -> None:
        self._logger.info("Closing MariaDB connection")
        self.cursor.close()
        self.conn.close()
