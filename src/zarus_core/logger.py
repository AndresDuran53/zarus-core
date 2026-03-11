"""Shared logging utility designed to be reused as a package dependency.

Key behavior:
- A single project logger context is shared process-wide.
- All classes using ``CustomLogging`` default to the same project log file.
- Component/class loggers are created as children of the same project name.
- Host projects can configure the context once via ``configure_project``.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from threading import Lock
from typing import Any, Optional


class _JSONFormatter(logging.Formatter):
    """JSON formatter using only Python standard library."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
        }

        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class CustomLogging:
    """Reusable logging facade with project-wide shared logging context."""

    _instances: dict[tuple[str, str], "CustomLogging"] = {}
    _lock = Lock()

    _project_name: Optional[str] = None
    _project_log_file: Optional[str] = None
    _project_level: int = logging.INFO
    _project_console: bool = True
    _project_console_level: Optional[int] = None
    _project_max_bytes: int = 10 * 1024 * 1024
    _project_backup_count: int = 5
    _project_json_format: bool = False
    _project_datefmt: str = "%d-%m-%Y %H:%M:%S"
    _project_initialized: bool = False

    @classmethod
    def configure_project(
        cls,
        project_name: Optional[str] = None,
        log_file: Optional[str] = None,
        level: int | str = logging.INFO,
        console: bool = True,
        console_level: Optional[int | str] = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        json_format: bool = False,
        datefmt: str = "%d-%m-%Y %H:%M:%S",
        force_reconfigure: bool = False,
    ) -> None:
        """Configure shared project logging context for all package classes."""
        with cls._lock:
            if cls._project_initialized and not force_reconfigure:
                return

            cls._project_name = project_name or cls._detect_project_name()
            cls._project_level = cls._resolve_level(level)
            cls._project_console = console
            cls._project_console_level = (
                cls._resolve_level(console_level) if console_level is not None else None
            )
            cls._project_max_bytes = max_bytes
            cls._project_backup_count = backup_count
            cls._project_json_format = json_format
            cls._project_datefmt = datefmt

            env_log_file = Path(
                Path.cwd(),
                "logs",
                f"{cls._project_name}.log",
            )
            cls._project_log_file = str(Path(log_file)) if log_file else str(env_log_file)

            project_logger = logging.getLogger(cls._project_name)
            project_logger.setLevel(cls._project_level)
            project_logger.propagate = False
            project_logger.handlers.clear()

            standard_formatter = logging.Formatter(
                fmt="[%(asctime)s] %(levelname)s - [%(name)s:%(module)s:%(funcName)s:%(lineno)d] - %(message)s",
                datefmt=cls._project_datefmt,
            )
            json_formatter = _JSONFormatter(datefmt=cls._project_datefmt)

            file_path = Path(cls._project_log_file)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                filename=file_path,
                maxBytes=cls._project_max_bytes,
                backupCount=cls._project_backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(cls._project_level)
            file_handler.setFormatter(json_formatter if cls._project_json_format else standard_formatter)
            project_logger.addHandler(file_handler)

            if cls._project_console:
                stream_handler = logging.StreamHandler()
                stream_handler.setLevel(
                    cls._project_console_level if cls._project_console_level is not None else cls._project_level
                )
                stream_handler.setFormatter(json_formatter if cls._project_json_format else standard_formatter)
                project_logger.addHandler(stream_handler)

            cls._project_initialized = True

    @classmethod
    def _ensure_project_configured(cls) -> None:
        if cls._project_initialized:
            return
        cls.configure_project(
            project_name=None,
            log_file=None,
            level=logging.INFO,
            console=True,
            json_format=False,
        )

    @staticmethod
    def _detect_project_name() -> str:
        """Best-effort project name detection for package consumers."""
        env_name = None
        try:
            import os

            env_name = os.getenv("CUSTOM_LOGGING_PROJECT") or os.getenv("LOG_PROJECT_NAME")
        except Exception:
            env_name = None

        if env_name:
            return env_name

        argv0 = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else ""
        if argv0 and argv0 not in {"-c", "__main__", "python", "python3"}:
            return argv0

        cwd_name = Path.cwd().name
        return cwd_name or "app"

    @classmethod
    def get_project_context(cls) -> dict[str, Any]:
        """Return current shared logging context."""
        cls._ensure_project_configured()
        return {
            "project_name": cls._project_name,
            "log_file": cls._project_log_file,
            "level": cls._project_level,
            "console": cls._project_console,
            "console_level": cls._project_console_level,
            "json_format": cls._project_json_format,
        }

    def __new__(cls, *args: Any, **kwargs: Any) -> "CustomLogging":
        logger_name = kwargs.get("logger_name") or kwargs.get("component_name")
        if logger_name is None and args:
            logger_name = args[0]

        if logger_name is None:
            logger_name = "General"

        cls._ensure_project_configured()
        project_name = cls._project_name or "app"
        key = (project_name, str(logger_name))

        with cls._lock:
            instance = cls._instances.get(key)
            if instance is None:
                instance = super().__new__(cls)
                cls._instances[key] = instance
        return instance

    def __init__(
        self,
        component_name: Optional[str] = None,
        logger_name: Optional[str] = None,
        log_file: Optional[str] = None,
        level: Optional[int | str] = None,
        console: Optional[bool] = None,
        console_level: Optional[int | str] = None,
        max_bytes: Optional[int] = None,
        backup_count: Optional[int] = None,
        json_format: Optional[bool] = None,
        datefmt: Optional[str] = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self._ensure_project_configured()

        selected_component = component_name or logger_name or "General"

        if any(value is not None for value in (log_file, level, console, console_level, max_bytes, backup_count, json_format, datefmt)):
            self.configure_project(
                project_name=self._project_name,
                log_file=log_file or self._project_log_file,
                level=level if level is not None else self._project_level,
                console=console if console is not None else self._project_console,
                console_level=console_level if console_level is not None else self._project_console_level,
                max_bytes=max_bytes if max_bytes is not None else self._project_max_bytes,
                backup_count=backup_count if backup_count is not None else self._project_backup_count,
                json_format=json_format if json_format is not None else self._project_json_format,
                datefmt=datefmt if datefmt is not None else self._project_datefmt,
                force_reconfigure=True,
            )

        self.project_name = self._project_name or "app"
        self.component_name = selected_component
        self.logger_name = f"{self.project_name}.{self.component_name}"
        self.log_file = self._project_log_file

        project_logger = logging.getLogger(self.project_name)
        self._logger = project_logger.getChild(self.component_name)
        self._logger.setLevel(project_logger.level)
        self._logger.propagate = True

        self._initialized = True

    def __repr__(self) -> str:
        return (
            f"<CustomLogging project_name={self.project_name} "
            f"component_name={self.component_name} log_file={self.log_file}>"
        )

    @staticmethod
    def _resolve_level(level: int | str) -> int:
        if isinstance(level, int):
            return level
        return getattr(logging, str(level).upper(), logging.INFO)

    def get_logger(self) -> logging.Logger:
        """Return underlying configured logger."""
        return self._logger

    def set_level(self, level: int | str) -> None:
        """Update logger and handler levels."""
        resolved = self._resolve_level(level)
        self._logger.setLevel(resolved)
        for handler in self._logger.handlers:
            handler.setLevel(resolved)

    def log(self, level: int | str, message: str, **extra: Any) -> None:
        """Generic logging method."""
        resolved = self._resolve_level(level)
        self._logger.log(resolved, str(message), extra=extra or None)

    def debug(self, message: str, **extra: Any) -> None:
        self._logger.debug(str(message), extra=extra or None)

    def info(self, message: str, **extra: Any) -> None:
        self._logger.info(str(message), extra=extra or None)

    def warning(self, message: str, **extra: Any) -> None:
        self._logger.warning(str(message), extra=extra or None)

    def error(self, message: str, **extra: Any) -> None:
        self._logger.error(str(message), extra=extra or None)

    def critical(self, message: str, **extra: Any) -> None:
        self._logger.critical(str(message), extra=extra or None)

    def exception(self, message: str, **extra: Any) -> None:
        """Log exception with stack trace (use inside except block)."""
        self._logger.exception(str(message), extra=extra or None)