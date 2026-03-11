from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class ApiConfig:
    """Abstracción genérica para servicios API configurados en JSON."""

    service_name: str
    secret_token: str
    base_url: str
    api_endpoints: Dict[str, str]

    @classmethod
    def from_config(cls, config: Dict[str, Any], service_name: str) -> "ApiConfig":
        service_config = config.get(service_name)
        if not isinstance(service_config, dict):
            raise ValueError(f"Falta la configuración obligatoria '{service_name}'.")

        host = cls._require_value(service_config, "host", parent=service_name)
        secret_token = cls._require_value(service_config, "secretToken", parent=service_name)
        port = cls._require_value(service_config, "port", parent=service_name, can_be_empty=True)
        apis = cls._require_value(service_config, "apis", parent=service_name, can_be_empty=True)

        api_endpoints: Dict[str, str] = {}
        for index, api in enumerate(apis):
            if not isinstance(api, dict):
                raise ValueError(f"La entrada '{service_name}.apis[{index}]' debe ser un objeto.")

            api_name = cls._require_value(api, "name", parent=f"{service_name}.apis[{index}]")
            endpoint = cls._require_value(api, "endpoint", parent=f"{service_name}.apis[{index}]")

            if api_name in api_endpoints:
                raise ValueError(f"La API '{api_name}' está duplicada en '{service_name}.apis'.")

            api_endpoints[api_name] = endpoint

        base_host = host.rstrip("/")
        base_url = f"{base_host}:{port}" if port else base_host

        return cls(
            service_name=service_name,
            secret_token=secret_token,
            base_url=base_url,
            api_endpoints=api_endpoints,
        )

    def get_endpoint(self, api_name: str) -> str | None:
        if api_name not in self.api_endpoints:
            return None
        return self.api_endpoints[api_name]

    def get_full_url(self, api_name: str) -> str:
        endpoint = self.get_endpoint(api_name)
        if endpoint is None:
            raise ValueError(f"No existe endpoint para la API '{api_name}' en '{self.service_name}.apis'.")
        return f"{self.base_url}{endpoint}"

    @staticmethod
    def _require_value(
        source: Dict[str, Any],
        key: str,
        *,
        parent: str,
        can_be_empty: bool = False,
    ) -> Any:
        value = source.get(key)
        if value is None:
            raise ValueError(f"Falta la configuración obligatoria '{parent}.{key}'.")

        config_value = value

        if can_be_empty: return config_value

        if isinstance(value, str) and not value.strip():
            raise ValueError(
                f"La configuración obligatoria '{parent}.{key}' no puede estar vacía."
                )
        elif isinstance(value, list) and not value:
            raise ValueError(
                f"La configuración obligatoria '{parent}.{key}' no puede ser una lista vacía."
                )
        elif isinstance(value, dict) and not value:
            raise ValueError(
                f"La configuración obligatoria '{parent}.{key}' no puede ser un objeto vacío."
                )

        return config_value
