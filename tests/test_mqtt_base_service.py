from types import SimpleNamespace

import zarus_core.mqtt_base_service as mqtt_module
from zarus_core.mqtt_base_service import MqttBaseService, MqttConfig


class _FakeMqttClient:
    def __init__(self, *args, **kwargs):
        self.on_message = None
        self.on_connect = None
        self.on_disconnect = None
        self.connect_calls = []
        self.loop_started = 0
        self.loop_stopped = 0
        self.disconnect_calls = 0

    def username_pw_set(self, username, password):
        self.username = username
        self.password = password

    def connect(self, host, port):
        self.connect_calls.append((host, port))

    def loop_start(self):
        self.loop_started += 1

    def loop_stop(self):
        self.loop_stopped += 1

    def disconnect(self):
        self.disconnect_calls += 1

    def subscribe(self, topic):
        return SimpleNamespace(rc=0)


class _FakeMqttFactory:
    def __init__(self):
        self.clients = []

    def __call__(self, *args, **kwargs):
        client = _FakeMqttClient(*args, **kwargs)
        self.clients.append(client)
        return client


def _make_service(monkeypatch):
    factory = _FakeMqttFactory()
    monkeypatch.setattr(mqtt_module.mqtt, "Client", factory)

    config = MqttConfig(
        broker_address="localhost",
        mqtt_user="user",
        mqtt_pass="pass",
        subscription_topics=[{"topic": "devices/+/status", "commandName": "status"}],
    )

    service = MqttBaseService(
        config=config,
        client_id="test-client",
        message_handler=lambda *_: None,
        auto_connect=False,
    )
    return service, factory


def test_is_connected_updates_on_connect_disconnect_and_reconnect(monkeypatch):
    service, _ = _make_service(monkeypatch)

    assert service.is_connected() is False

    service.connect()
    assert service.is_connected() is False

    service._on_connect(service.client, None, None, 0)
    assert service.is_connected() is True

    service._on_disconnect(service.client, None, 1)
    assert service.is_connected() is False

    service._on_connect(service.client, None, None, 0)
    assert service.is_connected() is True


def test_disconnect_resets_state_and_stops_client_loop(monkeypatch):
    service, factory = _make_service(monkeypatch)

    service.connect()
    service._on_connect(service.client, None, None, 0)

    service.disconnect()

    assert service.is_connected() is False
    fake_client = factory.clients[0]
    assert fake_client.loop_stopped == 1
    assert fake_client.disconnect_calls == 1


def test_failed_on_connect_keeps_service_disconnected(monkeypatch):
    service, _ = _make_service(monkeypatch)

    service.connect()
    service._on_connect(service.client, None, None, 5)

    assert service.is_connected() is False
