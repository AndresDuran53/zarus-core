"""Public package exports for zarus_core."""

from .config import ConfigurationReader, load_settings
from .logging import CustomLogging

try:
    from .mqtt import MqttBaseService, MqttConfig
except Exception:
    MqttBaseService = None  # type: ignore[assignment]
    MqttConfig = None  # type: ignore[assignment]

__all__ = [
    "ConfigurationReader",
    "CustomLogging",
    "load_settings",
]

if MqttBaseService is not None and MqttConfig is not None:
    __all__.extend(["MqttBaseService", "MqttConfig"])
