"""Common exceptions for zarus_core package."""


class ZarusCoreError(Exception):
    """Base exception for zarus_core."""


class ConfigurationError(ZarusCoreError):
    """Raised when configuration files are invalid or unreadable."""


class MqttServiceError(ZarusCoreError):
    """Raised for MQTT service lifecycle and runtime errors."""


class MariaDBClientError(ZarusCoreError):
    """Raised for MariaDB client initialization and runtime errors."""
