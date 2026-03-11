"""
Examples demonstrating how to use MqttBaseService in your logic classes

The MqttBaseService abstracts all MQTT complexity, allowing your logic classes
to focus on business logic while easily receiving inputs and sending outputs.

Run from project root:
    python examples/mqtt_base_service_example.py
"""

from zarus_core import MqttBaseService, MqttConfig, CustomLogging
import logging


# ==================== EXAMPLE 1: Simple Service ====================
# A service that receives commands and sends responses

def simple_message_handler(topic: str, payload: str, command_name: str = None):
    """
    Simple handler for incoming MQTT messages.
    This is called automatically when a message arrives on subscribed topics.
    """
    print(f"\n[INPUT RECEIVED]")
    print(f"  Topic: {topic}")
    print(f"  Command: {command_name}")
    print(f"  Payload: {payload}")


def example_simple_service():
    """Example: Simple service using MqttBaseService"""
    
    # Configuration (normally loaded from JSON)
    config_data = {
        "mqtt": {
            "brokerAddress": "localhost",
            "mqttUser": "user",
            "mqttPass": "password",
            "subscriptionTopics": [
                {"topic": "home/command/light", "commandName": "toggle_light"},
                {"topic": "home/command/temperature", "commandName": "set_temperature"}
            ],
            "publishTopics": [
                {"topic": "home/status/light", "commandName": "light_status"},
                {"topic": "home/status/temperature", "commandName": "temperature_status"}
            ]
        }
    }
    
    # Create config and service
    config = MqttConfig.from_json(config_data)
    mqtt = MqttBaseService(
        config=config,
        client_id="SimpleService",
        message_handler=simple_message_handler
    )
    
    # Send output to users/systems
    mqtt.publish("home/status/light", "ON")
    mqtt.publish_by_command("temperature_status", "22°C")
    
    # Keep running (in real app, this would be your main loop)
    # input("Press Enter to stop...\n")
    
    # Cleanup
    mqtt.disconnect()


# ==================== EXAMPLE 2: Logic Class with MQTT ====================
# A proper class that encapsulates business logic and uses MQTT for I/O

class TemperatureController:
    """
    Example logic class that uses MQTT for input/output.
    
    This demonstrates how to integrate MQTT into your business logic classes
    without polluting them with MQTT implementation details.
    """
    
    def __init__(self, config: MqttConfig, client_id: str = "TemperatureController"):
        self.current_temperature = 20.0
        self.target_temperature = 22.0
        
        # Initialize MQTT service with our message handler
        self.mqtt = MqttBaseService(
            config=config,
            client_id=client_id,
            message_handler=self.handle_mqtt_message,
            logger=self._setup_logger()
        )
    
    def _setup_logger(self):
        """Setup a custom logger for this service"""
        logger = logging.getLogger("TemperatureController")
        logger.setLevel(logging.INFO)
        return logger
    
    def handle_mqtt_message(self, topic: str, payload: str, command_name: str = None):
        """
        Handle incoming MQTT messages (INPUT/TRIGGER).
        This is the entry point for all external triggers.
        """
        if command_name == "set_target_temperature":
            self.set_target_temperature(float(payload))
        elif command_name == "get_current_temperature":
            self.report_current_temperature()
        elif command_name == "update_sensor":
            self.update_from_sensor(float(payload))
        else:
            print(f"Unknown command: {command_name}")
    
    def set_target_temperature(self, target: float):
        """Business logic: Set target temperature"""
        self.target_temperature = target
        print(f"Target temperature set to: {target}°C")
        
        # Send result back (OUTPUT)
        self.mqtt.publish_by_command("temperature_status", 
                                     f"Target set to {target}°C")
        
        # Trigger adjustment if needed
        self.adjust_temperature()
    
    def update_from_sensor(self, temperature: float):
        """Business logic: Update from sensor reading"""
        self.current_temperature = temperature
        print(f"Sensor reading: {temperature}°C")
        
        # Send output
        self.mqtt.publish("home/sensor/temperature/current", str(temperature))
        
        # Check if adjustment needed
        self.adjust_temperature()
    
    def adjust_temperature(self):
        """Business logic: Adjust heating/cooling"""
        diff = self.target_temperature - self.current_temperature
        
        if abs(diff) > 0.5:
            action = "heating" if diff > 0 else "cooling"
            print(f"Adjusting: {action}")
            
            # Send output to HVAC system
            self.mqtt.publish("home/hvac/command", action)
    
    def report_current_temperature(self):
        """Send current temperature status (OUTPUT)"""
        status = {
            "current": self.current_temperature,
            "target": self.target_temperature
        }
        # In real app, you'd use JSON
        self.mqtt.publish_by_command("temperature_status", str(status))
    
    def shutdown(self):
        """Cleanup when service stops"""
        print("Shutting down Temperature Controller")
        self.mqtt.disconnect()


def example_logic_class():
    """Example: Using MQTT in a logic class"""
    
    config_data = {
        "mqtt": {
            "brokerAddress": "localhost",
            "mqttUser": "user",
            "mqttPass": "password",
            "subscriptionTopics": [
                {"topic": "home/temperature/set", "commandName": "set_target_temperature"},
                {"topic": "home/temperature/get", "commandName": "get_current_temperature"},
                {"topic": "home/sensor/+/update", "commandName": "update_sensor"}
            ],
            "publishTopics": [
                {"topic": "home/temperature/status", "commandName": "temperature_status"}
            ]
        }
    }
    
    config = MqttConfig.from_json(config_data)
    controller = TemperatureController(config)
    
    # Simulate some operations
    # In real app, these would come from MQTT messages
    controller.update_from_sensor(19.5)
    controller.set_target_temperature(23.0)
    
    # Keep running
    # input("Press Enter to stop...\n")
    
    controller.shutdown()


# ==================== EXAMPLE 3: Context Manager Usage ====================
# Using 'with' statement for automatic connection/disconnection

def example_context_manager():
    """Example: Using context manager for automatic cleanup"""
    
    config_data = {
        "mqtt": {
            "brokerAddress": "localhost",
            "mqttUser": "user",
            "mqttPass": "password",
            "subscriptionTopics": [
                {"topic": "home/events/#", "commandName": "any_event"}
            ]
        }
    }
    
    def event_handler(topic: str, payload: str, command_name: str = None):
        print(f"Event: {topic} = {payload}")
    
    config = MqttConfig.from_json(config_data)
    
    # Automatic connection and cleanup
    with MqttBaseService(config, "EventListener", event_handler) as mqtt:
        mqtt.publish("home/events/startup", "Service started")
        # Do work...
        mqtt.publish("home/events/status", "Running")
    
    # mqtt.disconnect() called automatically


# ==================== EXAMPLE 4: Dynamic Subscription ====================
# Adding/removing subscriptions at runtime

def example_dynamic_subscription():
    """Example: Adding subscriptions dynamically"""
    
    config_data = {
        "mqtt": {
            "brokerAddress": "localhost",
            "mqttUser": "user",
            "mqttPass": "password",
            "subscriptionTopics": []  # Start with no subscriptions
        }
    }
    
    messages_received = []
    
    def dynamic_handler(topic: str, payload: str, command_name: str = None):
        messages_received.append((topic, payload, command_name))
        print(f"Received on {topic}: {payload}")
    
    config = MqttConfig.from_json(config_data)
    mqtt = MqttBaseService(config, "DynamicService", dynamic_handler)
    
    # Subscribe to topics based on runtime conditions
    mqtt.subscribe("home/sensor/living_room", "living_room_sensor")
    mqtt.subscribe("home/sensor/bedroom", "bedroom_sensor")
    
    # Later, can unsubscribe
    mqtt.unsubscribe("home/sensor/bedroom")
    
    mqtt.disconnect()


# ==================== EXAMPLE 5: Error Handling ====================
# Robust error handling in message handler

class RobustService:
    """Example: Service with proper error handling"""
    
    def __init__(self, config: MqttConfig):
        self.mqtt = MqttBaseService(
            config=config,
            client_id="RobustService",
            message_handler=self.safe_message_handler
        )
    
    def safe_message_handler(self, topic: str, payload: str, command_name: str = None):
        """
        Message handler with error handling.
        Exceptions here won't crash the MQTT loop.
        """
        try:
            # Process message
            result = self.process_command(command_name, payload)
            
            # Send success response
            self.mqtt.publish(f"{topic}/result", f"success: {result}")
            
        except ValueError as e:
            # Send error response
            self.mqtt.publish(f"{topic}/error", f"Invalid input: {e}")
            
        except Exception as e:
            # Log and send generic error
            print(f"Error processing {command_name}: {e}")
            self.mqtt.publish(f"{topic}/error", "Processing failed")
    
    def process_command(self, command: str, data: str):
        """Business logic that might raise exceptions"""
        if command == "calculate":
            return eval(data)  # Don't do this in production!
        elif command == "validate":
            if not data.isdigit():
                raise ValueError("Data must be numeric")
            return int(data)
        else:
            raise ValueError(f"Unknown command: {command}")


# ==================== MAIN ====================

if __name__ == "__main__":
    print("MQTT Base Service Examples")
    print("=" * 50)
    
    # Uncomment to run examples:
    
    # print("\n1. Simple Service Example")
    # example_simple_service()
    
    # print("\n2. Logic Class Example")
    # example_logic_class()
    
    # print("\n3. Context Manager Example")
    # example_context_manager()
    
    # print("\n4. Dynamic Subscription Example")
    # example_dynamic_subscription()
    
    print("\nExamples defined. Uncomment to run.")
    print("\nKey Concepts:")
    print("- INPUT: Messages received trigger your handler function")
    print("- OUTPUT: Use publish() or publish_by_command() to send results")
    print("- The MqttBaseService handles all MQTT complexity")
    print("- Your logic classes stay clean and focused on business logic")
