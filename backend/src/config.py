from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ocds_data"
    db_user: str = "user"
    db_password: str = "password"
    db_sslmode: str = "prefer"
    # Adaptador DNCP (fuente OCDS específica de Paraguay)
    dncp_api_base_url: str = "https://www.contrataciones.gov.py/datos/api/v3/doc"
    dncp_request_token: str | None = None
    dncp_rate_limit_sleep_seconds: int = 60

    # Motor de sincronización
    sync_max_concurrent_requests: int = 3
    source_timezone: str = (
        "America/Asuncion"  # zona horaria de la fuente para fecha_desde
    )
    default_start_date: str = "2026-01-01"  # Si no hay datos históricos
    sync_interval_hours: int = 6
    internal_secret: str = "change-me"  # canal worker -> api para invalidar cache.
    api_internal_url: str = "http://api:8000"
    indicators_start_date: str = "2020-01-01"  # Indicadores: inicia desde esta fecha.
    cors_allow_origins: str = "*"  # CORS API
    debug_flatten_output: bool = False
    debug_flatten_dir: str = "data/debug_flatten"
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore"  # Ignora campos extra
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()
