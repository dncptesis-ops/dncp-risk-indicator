"""
Worker para sincronizacion.
* Sincronizacion con una fuente OCDS (adaptador DNCP).
* Actualizacion de vista.
* Invalida cache de /common

Se ejecuta con: python -m src.interfaces.worker
"""

import logging
import logging.config
import time
from pathlib import Path

import requests
import yaml

from src.application.sync_service import SyncService
from src.config import settings
from src.etl.ocds_flatten_ingest import ETLService
from src.infrastructure.database import DatabaseRepository
from src.infrastructure.dncp_client import DNCPClient

# El logger se sigue obteniendo igual, pero ahora la configuración
# se cargará desde el archivo YAML si existe.
logger = logging.getLogger(__name__)

DSN = (
    f"postgresql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    f"?sslmode={settings.db_sslmode}"
)


def _setup_logging() -> None:
    """Carga log_config.yaml para ver los INFO del sync."""
    cfg = Path(__file__).resolve().parents[2] / "log_config.yaml"
    if cfg.exists():
        with cfg.open("r", encoding="utf-8") as f:
            logging.config.dictConfig(yaml.safe_load(f))
    else:
        logging.basicConfig(level=logging.INFO)


def _invalidate_api_cache() -> None:
    """Avisa a la API para invalidar cache de /common."""
    try:
        resp = requests.post(
            f"{settings.api_internal_url}/internal/invalidate-cache",
            headers={"x-internal-secret": settings.internal_secret},
            timeout=80,
        )
        if not resp.ok:
            logger.warning(f"Invalidación de cache no ok: {resp.status_code}")
    except Exception as e:
        logger.warning(f"No se pudo invalidar la cache de la API: {e}")


def _connect_with_retries() -> DatabaseRepository:
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            return DatabaseRepository(DSN)
        except Exception as e:
            logger.error(
                f"Intento {attempt}/{max_retries} de conexión a BD fallido: {e}"
            )
            if attempt == max_retries:
                raise RuntimeError("No se pudo conectar a la base de datos") from e
            time.sleep(30)


def main() -> None:
    _setup_logging()

    db_repo = _connect_with_retries()

    try:
        db_repo.reconcile_stale_runs()

        dncp_client = DNCPClient()
        etl_service = ETLService(db_repo)
        sync_service = SyncService(
            db_repo=db_repo,
            source_client=dncp_client,
            etl_service=etl_service,
            start_date=settings.default_start_date,
        )

        while True:
            try:
                logger.info("Sync triggered")
                db_repo.reconnect_if_closed()
                processed = sync_service.sync_once()
                logger.info(f"Sync completada: {processed} releases procesados")
                db_repo.refresh_materialized_view("party_master")
                logger.info("party_master refrescado correctamente")
                _invalidate_api_cache()
            except Exception as e:
                logger.error(f"Error en worker sync: {e}")
            time.sleep(settings.sync_interval_hours * 3600)
    finally:
        db_repo.close()


if __name__ == "__main__":
    main()
