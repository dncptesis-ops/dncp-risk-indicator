"""Base PostgreSQL temporal con el conjunto de datos controlado.

Las pruebas de integración necesitan un PostgreSQL local (el de
docker-compose.local.yml). Si no hay uno, se saltean. La conexión no sale del .env:
se usa TEST_DATABASE_URL o, si no está, el PostgreSQL local. Se crea una base nueva
para las pruebas y se borra al terminar.
"""

import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import pytest

from src.config import settings
from src.etl.ocds_flatten_ingest import ETL_MAPPING, ETLService
from src.infrastructure.database import DatabaseRepository
from tests.integration.datos_controlados import escribir_csvs

ADMIN_DSN = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://ocds_user:ocds_password@localhost:5432/ocds_data"
)
SCHEMA = Path(__file__).resolve().parents[2] / "schema.sql"


@pytest.fixture(scope="session")
def base_temporal():
    """Crea una base vacía con schema.sql y la borra al final."""
    try:
        admin = psycopg2.connect(ADMIN_DSN, connect_timeout=3)
    except psycopg2.OperationalError:
        pytest.skip("No hay un PostgreSQL local para las pruebas de integración")
    admin.autocommit = True
    nombre = f"ocds_prueba_{uuid.uuid4().hex[:8]}"
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{nombre}"')
    dsn = urlparse(ADMIN_DSN)._replace(path=f"/{nombre}").geturl()

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.close()

    yield dsn

    with admin.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (nombre,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{nombre}"')
    admin.close()


def cargar_csvs(dsn: str, carpeta: Path) -> None:
    """Carga los CSV igual que el ETL histórico: mapeos, retención y party_master."""
    db = DatabaseRepository(dsn)
    try:
        etl = ETLService(db)
        for mapping in ETL_MAPPING:
            etl.process_mapping(carpeta, mapping)
        db.prune_all_old_releases()
        db.refresh_materialized_view("party_master")
    finally:
        db.close()


@pytest.fixture(scope="session")
def datos_cargados(base_temporal, tmp_path_factory):
    """Escribe los CSV de prueba en una carpeta 2024/ y los carga con el ETL real."""
    inicio_original = settings.indicators_start_date
    settings.indicators_start_date = "2020-01-01"  # no depende del .env local

    carpeta = tmp_path_factory.mktemp("csv") / "2024"
    carpeta.mkdir()
    escribir_csvs(carpeta)
    cargar_csvs(base_temporal, carpeta)

    yield {"dsn": base_temporal, "carpeta": carpeta}

    settings.indicators_start_date = inicio_original
