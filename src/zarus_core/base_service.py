"""
MQTT Base Service - Abstraction layer for MQTT communication

This class abstracts all MQTT client complexity and provides a simple interface
for logic classes to:
- Subscribe to topics (receive input/triggers)
- Publish messages (send output/results)
- Handle incoming messages with callbacks

Usage Example:
    # Define your message handler
    def handle_message(topic: str, payload: str, command_name: str = None):
        print(f"Received {payload} on {topic} for command {command_name}")
    
    # Create service
    config = MqttConfig.from_json(config_data)
    mqtt = MqttBaseService(
        config=config,
        client_id="MyService",
        message_handler=handle_message
    )
    
    # Send output
    mqtt.publish("home/status", "ready")
"""

import paho.mqtt.client as mqtt
from typing import Callable, Optional, List, Dict, Any
import logging

from .exceptions import MqttServiceError
from .logger import CustomLogging


class MqttConfig:
    """Configuration container for MQTT connection and topics"""
    
    def __init__(
        self, 
        broker_address: str,
        mqtt_user: str,
        mqtt_pass: str,
        subscription_topics: Optional[List[Dict[str, str]]] = None,
        publish_topics: Optional[List[Dict[str, str]]] = None,
        port: int = 1883
    ):
        """
        Initialize MQTT configuration.
        
        Args:
            broker_address: MQTT broker hostname/IP
            mqtt_user: Username for authentication
            mqtt_pass: Password for authentication
            subscription_topics: List of dicts with 'topic' and optional 'commandName'
            publish_topics: List of dicts with 'topic' and optional 'commandName'
            port: MQTT broker port (default: 1883)
        """
        self.broker_address = broker_address
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        self.subscription_topics = subscription_topics or []
        self.publish_topics = publish_topics or []
        self.port = port

    @classmethod
    def from_json(cls, config_data: dict) -> 'MqttConfig':
        """
        Create MqttConfig from JSON configuration data.
        
        Args:
            config_data: Dictionary containing 'mqtt' section with configuration
            
        Returns:
            MqttConfig instance
        """
        mqtt_data = config_data.get('mqtt', {})
        return cls(
            broker_address=mqtt_data.get('brokerAddress') or mqtt_data.get('broker_address'),
            mqtt_user=mqtt_data.get('mqttUser') or mqtt_data.get('mqtt_user'),
            mqtt_pass=mqtt_data.get('mqttPass') or mqtt_data.get('mqtt_pass'),
            subscription_topics=mqtt_data.get('subscriptionTopics', []),
            publish_topics=mqtt_data.get('publishTopics', []),
            port=mqtt_data.get('port', 1883)
        )


class MqttBaseService:
    """
    Base MQTT Service - Abstracts MQTT client complexity
    
    This class handles all MQTT communication details and provides a clean
    interface for logic classes to receive inputs and send outputs.
    """
    
    def __init__(
        self,
        config: MqttConfig,
        client_id: str,
        message_handler: Callable[[str, str, Optional[str]], None],
        logger: Optional[logging.Logger] = None,
        auto_connect: bool = True
    ):
        """
        Initialize MQTT Base Service.
        
        Args:
            config: MqttConfig instance with connection details
            client_id: Unique identifier for this MQTT client
            message_handler: Callback function(topic, payload, command_name)
            logger: Optional logger instance (creates default if None)
            auto_connect: Whether to connect automatically (default: True)
        """
        self.config = config
        self.client_id = client_id
        self.message_handler = message_handler
        self.logger = logger or self._create_default_logger()
        
        # Topic mappings
        self._topic_to_command: Dict[str, str] = {}
        self._command_to_topic: Dict[str, str] = {}
        self._build_topic_mappings()
        
        # MQTT Client setup
        self.client: Optional[mqtt.Client] = None
        self._is_connected = False
        
        if auto_connect:
            self.connect()
    
    def _create_default_logger(self) -> logging.Logger:
        """Create a default logger if none provided"""
        return CustomLogging(
            component_name=f"MqttService.{self.client_id}",
        ).get_logger()
    
    def _build_topic_mappings(self):
        """Build internal mappings between topics and command names"""
        # Map subscription topics
        for topic_config in self.config.subscription_topics:
            topic = topic_config['topic']
            command = topic_config['commandName']
            self._topic_to_command[topic] = command
        
        # Map publish topics
        for topic_config in self.config.publish_topics:
            topic = topic_config['topic']
            command = topic_config['commandName']
            self._command_to_topic[command] = topic
    
    def connect(self):
        """Establish connection to MQTT broker and subscribe to topics"""
        if self._is_connected:
            self.logger.warning("Already connected to MQTT broker")
            return
        
        self.logger.info(f"Connecting to MQTT broker at {self.config.broker_address}")
        
        # Create MQTT client
        self.client = mqtt.Client(
            client_id=self.client_id,
            clean_session=False,
            userdata=None,
            protocol=mqtt.MQTTv311,
            transport="tcp"
        )
        client = self.client
        if client is None:
            self.logger.error("Failed to initialize MQTT client")
            raise MqttServiceError("MQTT client initialization returned None")
        
        # Set callbacks
        client.on_message = self._on_message_internal
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        
        # Set credentials
        client.username_pw_set(
            username=self.config.mqtt_user,
            password=self.config.mqtt_pass
        )
        
        # Connect to broker
        try:
            client.connect(self.config.broker_address, self.config.port)
            client.loop_start()
            self._is_connected = True
            self.logger.info("MQTT client connected and loop started")
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Internal callback when connection is established"""
        if rc == 0:
            self.logger.info("Successfully connected to MQTT broker")
            self._subscribe_to_topics()
        else:
            self.logger.error(f"Connection failed with result code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Internal callback when disconnected"""
        self._is_connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection. Result code: {rc}")
        else:
            self.logger.info("Disconnected from MQTT broker")
    
    def _subscribe_to_topics(self):
        """Subscribe to all configured topics"""
        if not self.client:
            self.logger.error("Cannot subscribe - MQTT client not initialized")
            return

        for topic_config in self.config.subscription_topics:
            topic = topic_config.get('topic')
            if topic:
                self.client.subscribe(topic)
                self.logger.info(f"Subscribed to topic: {topic}")
    
    def _on_message_internal(self, client, userdata, message):
        """
        Internal MQTT callback that processes incoming messages.
        Extracts topic and payload, then calls user's message_handler.
        """
        try:
            topic = message.topic
            payload = message.payload.decode("utf-8")
            
            self.logger.debug(f"[Received] Topic: {topic} | Payload: {payload}")
            
            # Get command name for this topic
            command_name = self.get_command_from_topic(topic)
            
            # Call user's message handler
            self.message_handler(topic, payload, command_name)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
    
    def get_command_from_topic(self, topic: str) -> Optional[str]:
        """
        Get command name associated with a topic.
        Supports both exact matching and wildcard matching with '+'.
        
        Args:
            topic: The topic to look up
            
        Returns:
            Command name if found, None otherwise
        """
        # First try exact match
        if topic in self._topic_to_command:
            return self._topic_to_command[topic]
        
        # Try wildcard matching
        topic_parts = topic.split("/")
        
        for configured_topic, command_name in self._topic_to_command.items():
            configured_parts = configured_topic.split("/")
            
            # Must have same number of parts
            if len(configured_parts) != len(topic_parts):
                continue
            
            # Check if all parts match (+ is wildcard)
            match = True
            for configured_part, topic_part in zip(configured_parts, topic_parts):
                if configured_part != '+' and configured_part != topic_part:
                    match = False
                    break
            
            if match:
                return command_name
        
        return None
    
    def get_topic_from_command(self, command_name: str) -> Optional[str]:
        """
        Get topic associated with a command name.
        
        Args:
            command_name: The command name to look up
            
        Returns:
            Topic if found, None otherwise
        """
        return self._command_to_topic.get(command_name)
    
    # ==================== PUBLIC API FOR LOGIC CLASSES ====================
    
    def publish(self, topic: str, message: str, qos: int = 1, retain: bool = False):
        """
        Publish a message to a topic (OUTPUT).
        
        This is the main method for sending results to users or other systems.
        
        Args:
            topic: MQTT topic to publish to
            message: Message payload (will be converted to string)
            qos: Quality of Service (0, 1, or 2) - default: 1
            retain: Whether to retain message on broker - default: False
        """
        if not self.client or not self._is_connected:
            self.logger.error("Cannot publish - not connected to MQTT broker")
            return
        
        message_str = str(message)
        self.logger.info(f"[Publishing] Topic: {topic} | Message: {message_str}")
        
        try:
            result = self.client.publish(topic, message_str, qos=qos, retain=retain)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                self.logger.error(f"Failed to publish message. Result code: {result.rc}")
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
    
    def publish_by_command(self, command_name: str, message: str, qos: int = 1, retain: bool = False):
        """
        Publish a message using a command name instead of direct topic (OUTPUT).
        
        Args:
            command_name: Name of the command (maps to topic in config)
            message: Message payload
            qos: Quality of Service - default: 1
            retain: Whether to retain message - default: False
        """
        topic = self.get_topic_from_command(command_name)
        if topic:
            self.publish(topic, message, qos, retain)
        else:
            self.logger.error(f"No topic found for command: {command_name}")
    
    def subscribe(self, topic: str, command_name: Optional[str] = None):
        """
        Subscribe to an additional topic at runtime (INPUT).
        
        Args:
            topic: MQTT topic to subscribe to
            command_name: Optional command name to associate with this topic
        """
        if not self.client:
            self.logger.error("Cannot subscribe - MQTT client not initialized")
            return
        
        self.client.subscribe(topic)
        self.logger.info(f"Subscribed to topic: {topic}")
        
        if command_name:
            self._topic_to_command[topic] = command_name
    
    def unsubscribe(self, topic: str):
        """
        Unsubscribe from a topic.
        
        Args:
            topic: MQTT topic to unsubscribe from
        """
        if not self.client:
            self.logger.error("Cannot unsubscribe - MQTT client not initialized")
            return
        
        self.client.unsubscribe(topic)
        self.logger.info(f"Unsubscribed from topic: {topic}")
        
        # Remove from mapping if exists
        self._topic_to_command.pop(topic, None)
    
    def disconnect(self):
        """Disconnect from MQTT broker and stop loop"""
        if self.client and self._is_connected:
            self.logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()
            self.client.disconnect()
            self._is_connected = False
    
    def is_connected(self) -> bool:
        """
        Check if currently connected to MQTT broker.
        
        Returns:
            True if connected, False otherwise
        """
        return self._is_connected
    
    # Context manager support
    def __enter__(self):
        """Enable 'with' statement usage"""
        if not self._is_connected:
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting 'with' block"""
        self.disconnect()
