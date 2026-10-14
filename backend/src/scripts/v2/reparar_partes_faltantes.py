"""
Repara procesos que quedaron sin partes (parties) después de la carga histórica.

El CSV de 2024 de la DNCP trae procesos sin ninguna fila en parties.csv, pero la
API sí las tiene. Este script los vuelve a bajar por API y los carga igual que
el worker.

Uso (desde backend/):

    uv run python -m src.scripts.v2.reparar_partes_faltantes            # solo informa
    uv run python -m src.scripts.v2.reparar_partes_faltantes --aplicar  # repara
    uv run python -m src.scripts.v2.reparar_partes_faltantes --aplicar --limite 20

Se puede cortar y volver a ejecutar.
"""

import argparse
import logging
import sys

from src.config import settings
from src.etl.flatten_adapter import record_to_dataframes
from src.etl.ocds_flatten_ingest import ETLService
from src.infrastructure.database import DatabaseRepository
from src.infrastructure.dncp_client import DNCPClient

logger = logging.getLogger("reparar_partes")

DSN = (
    f"postgresql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    f"?sslmode={settings.db_sslmode}"
)

# Procesos (versión vigente) sin ninguna fila en parties.
SQL_SIN_PARTES = """
    SELECT r.ocid, EXTRACT(YEAR FROM r.date)::int AS anio
    FROM latest_releases r
    WHERE NOT EXISTS (SELECT 1 FROM parties p WHERE p.release_id = r.release_id)
    ORDER BY r.date
"""


def procesos_sin_partes(db: DatabaseRepository) -> list[tuple[str, int]]:
    with db.conn.cursor() as cur:
        cur.execute(SQL_SIN_PARTES)
        filas = cur.fetchall()
    db.conn.commit()
    return filas


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--aplicar", action="store_true", help="descarga y carga los procesos")
    parser.add_argument("--limite", type=int, default=None, help="máximo de procesos a reparar")
    args = parser.parse_args(argv)

    db = DatabaseRepository(DSN)
    try:
        pendientes = procesos_sin_partes(db)
        por_anio: dict[int, int] = {}
        for _, anio in pendientes:
            por_anio[anio] = por_anio.get(anio, 0) + 1
        logger.info(f"Procesos sin partes: {len(pendientes)} {dict(sorted(por_anio.items()))}")

        if not args.aplicar:
            logger.info("Modo informe: no se modificó nada. Usar --aplicar para reparar.")
            return 0

        client = DNCPClient()
        etl = ETLService(db)
        ocids = [ocid for ocid, _ in pendientes][: args.limite]
        reparados, fallidos = 0, []
        for i, ocid in enumerate(ocids, 1):
            try:
                record = client.get_record(ocid)
                # el id se toma antes del flatten, que vacia el diccionario
                nuevo_id = record["records"][0]["compiledRelease"]["id"]
                etl.process_release_dataframes(record_to_dataframes(record))
                # se borra la version del CSV recien despues de cargar la nueva
                db.delete_other_versions(ocid, nuevo_id)
                reparados += 1
                logger.info(f"[{i}/{len(ocids)}] {ocid} reparado")
            except Exception as e:  # un proceso con error no corta la reparación
                fallidos.append(ocid)
                logger.error(f"[{i}/{len(ocids)}] {ocid} falló: {e}")

        if reparados:
            db.refresh_materialized_view("party_master")
        restantes = len(procesos_sin_partes(db))
        logger.info(
            f"Reparados: {reparados} | fallidos: {len(fallidos)} {fallidos[:10]} | "
            f"siguen sin partes: {restantes}"
        )
        return 1 if fallidos else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
