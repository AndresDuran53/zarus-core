"""Test configuration reader functionality."""

import json
from pathlib import Path

from zarus_core.config import ConfigurationReader


def test_config_reader_loads_json(tmp_path: Path):
    """Test that ConfigurationReader properly loads JSON files."""
    config_file = tmp_path / "test_config.json"
    test_data = {
        "mqtt": {
            "brokerAddress": "localhost",
            "mqttUser": "test_user",
            "mqttPass": "test_pass",
        }
    }
    
    config_file.write_text(json.dumps(test_data), encoding="utf-8")
    
    result = ConfigurationReader.read_config_file(str(config_file))
    
    assert result == test_data
    assert result["mqtt"]["brokerAddress"] == "localhost"
