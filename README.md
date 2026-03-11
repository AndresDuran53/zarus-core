# zarus-core

`zarus-core` is a reusable Python package for common service infrastructure components:

- **Shared project-level logging** (`CustomLogging`) - Singleton logging with project-wide context
- **JSON configuration loading** (`ConfigurationReader`) - Safe config file reading with error handling
- **MQTT abstraction layer** (`MqttBaseService`) - Clean MQTT pub/sub without boilerplate

## Installation

### For development (recommended)

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .

# Or with dev dependencies
pip install -e .[dev]
```

### As a dependency

```bash
pip install git+https://github.com/yourusername/zarus-core.git
```

Or add to your `pyproject.toml`:
```toml
dependencies = [
    "zarus-core @ git+https://github.com/yourusername/zarus-core.git"
]
```

## Quick Start

```python
from zarus_core import CustomLogging, ConfigurationReader, MqttBaseService, MqttConfig

# Configure project-wide logging once at startup
CustomLogging.configure_project(
    project_name="my_app",
    log_file="logs/my_app.log",
    level="INFO",
)

# Load configuration
config_data = ConfigurationReader.read_config_file("configuration.json")

# Create MQTT service
mqtt_config = MqttConfig.from_json(config_data)
service = MqttBaseService(
    config=mqtt_config,
    client_id="MyService",
    message_handler=lambda topic, payload, cmd: print(f"{cmd}: {payload}"),
)

# Publish messages
service.publish("home/status", "ready")
```

## Project Structure

```
zarus-core/
├── src/zarus_core/          # Main package (src-layout)
│   ├── config/              # Configuration utilities
│   │   ├── reader.py        #   ConfigurationReader
│   │   └── settings.py      #   Helper functions
│   ├── logging/             # Logging utilities
│   │   └── logger.py        #   CustomLogging
│   ├── mqtt/                # MQTT services
│   │   └── base_service.py  #   MqttBaseService, MqttConfig
│   ├── exceptions.py        # Package exceptions
│   └── __init__.py          # Public API
├── examples/                # Working examples
│   ├── mqtt_base_service_example.py
│   └── example_configuration.json
├── tests/                   # Test suite
├── pyproject.toml           # Package metadata & dependencies
├── .gitignore
├── LICENSE
└── README.md
```

## Features

### CustomLogging
- Project-wide singleton logger configuration
- Automatic log file rotation
- Console and file output
- Optional JSON formatting
- Component-based child loggers

### ConfigurationReader
- Safe JSON configuration loading
- UTF-8 encoding support
- Detailed error messages
- Built-in logging

### MqttBaseService
- Abstracted MQTT client management
- Topic-to-command mapping
- Wildcard topic support
- Context manager support
- Automatic reconnection

## Examples

See the [examples/](examples/) directory for complete working examples.

Run examples:
```bash
python examples/mqtt_base_service_example.py
```

## Running Tests

```bash
# Activate venv first
source .venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=zarus_core tests/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
