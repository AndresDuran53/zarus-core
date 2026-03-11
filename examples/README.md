# Examples

This directory contains working examples demonstrating how to use `zarus-core` in your projects.

## Files

- **mqtt_base_service_example.py** - Complete examples showing various MQTT service patterns
- **example_configuration.json** - Sample configuration template with all sections

## Running examples

First, install the package in development mode from the project root:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

Then run individual examples:

```bash
python examples/mqtt_base_service_example.py
```

## Configuration

Before running MQTT examples, update `example_configuration.json` with your broker credentials and copy it to your project root as `configuration.json`.
