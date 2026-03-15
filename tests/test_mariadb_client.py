from zarus_core.mariadb_client import MariaDBClient
import zarus_core.mariadb_client as mariadb_module


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self.closed = False

    def execute(self, query, params):
        self.executed.append((query, params))

    def fetchone(self):
        return ("one",)

    def fetchall(self):
        return [("one",), ("two",)]

    def close(self):
        self.closed = True


class _FakeConnection:
    def __init__(self, connected=True):
        self.connected = connected
        self.reconnect_calls = []
        self.commit_calls = 0
        self.closed = False
        self.cursor_instance = _FakeCursor()

    def cursor(self):
        return self.cursor_instance

    def is_connected(self):
        return self.connected

    def reconnect(self, attempts, delay):
        self.reconnect_calls.append((attempts, delay))
        self.connected = True

    def commit(self):
        self.commit_calls += 1

    def close(self):
        self.closed = True


class _FakeConnector:
    def __init__(self, connection):
        self.connection = connection
        self.connect_calls = []

    def connect(self, **kwargs):
        self.connect_calls.append(kwargs)
        return self.connection


def test_from_json_uses_defaults(monkeypatch):
    connection = _FakeConnection()
    connector = _FakeConnector(connection)
    monkeypatch.setattr(mariadb_module, "_mysql_connector", connector)

    client = MariaDBClient.from_json({"mariadb": {}})

    assert client.host == "localhost"
    assert client.reconnect_attempts == 5
    assert client.reconnect_delay == 2
    assert connector.connect_calls[0]["host"] == "localhost"


def test_ensure_connection_reconnects_when_disconnected(monkeypatch):
    connection = _FakeConnection(connected=False)
    connector = _FakeConnector(connection)
    monkeypatch.setattr(mariadb_module, "_mysql_connector", connector)

    client = MariaDBClient(
        host="localhost",
        user="user",
        password="pass",
        database="testdb",
        reconnect_attempts=3,
        reconnect_delay=1,
    )

    client.ensure_connection()

    assert connection.reconnect_calls == [(3, 1)]


def test_execute_fetch_and_close(monkeypatch):
    connection = _FakeConnection()
    connector = _FakeConnector(connection)
    monkeypatch.setattr(mariadb_module, "_mysql_connector", connector)

    client = MariaDBClient(
        host="localhost",
        user="user",
        password="pass",
        database="testdb",
    )

    client.execute("INSERT INTO t VALUES (%s)", params=("value",), commit=True)
    one = client.fetchone("SELECT 1")
    all_rows = client.fetchall("SELECT 1")
    client.close()

    assert connection.cursor_instance.executed[0] == ("INSERT INTO t VALUES (%s)", ("value",))
    assert connection.commit_calls == 1
    assert one == ("one",)
    assert all_rows == [("one",), ("two",)]
    assert connection.cursor_instance.closed is True
    assert connection.closed is True
