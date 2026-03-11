import json

from ..logging import CustomLogging

class ConfigurationReader():
    FILE_NAME = "configuration.json"
    _logger = CustomLogging(component_name="ConfigurationReader").get_logger()

    @staticmethod
    def read_config_file(fileName = FILE_NAME) -> dict:
        ConfigurationReader._logger.info(f"Reading configuration file: {fileName}")
        try:
            with open(fileName, "r", encoding="utf-8") as jsonfile:
                data = json.load(jsonfile)
            ConfigurationReader._logger.info("Configuration file loaded successfully")
            return data
        except FileNotFoundError:
            ConfigurationReader._logger.error(f"Configuration file not found: {fileName}")
            raise
        except json.JSONDecodeError as e:
            ConfigurationReader._logger.error(f"Invalid JSON in configuration file {fileName}: {e}")
            raise
        except Exception as e:
            ConfigurationReader._logger.exception(f"Unexpected error reading configuration file {fileName}: {e}")
            raise
