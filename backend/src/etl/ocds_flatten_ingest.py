"""
para procesar año en especifico:
docker compose run --rm api python -m src.etl.ocds_flatten_ingest --data-dir /app/data/2024

Para todos los años(obs cada año debe tener una carpeta principal con el año en formato yyyy):
docker compose run --rm api python -m src.etl.ocds_flatten_ingest --data-dir /app/data/historical --recursive

para ejecutar script desde hasta
uv run python -m src.etl.ocds_flatten_ingest --data-dir /Users/edu252/Downloads/procesos_completos/ --recursive --year-from 2020 --year-to 2026
"""

import argparse
import os
import hashlib
import logging
import re
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from typing import List, Dict, Any, Tuple

from src.infrastructure.database import DatabaseRepository
from src.config import settings

# ============================================================================
# MAPEO DE ARCHIVOS A TABLAS
# ============================================================================
# Orden estrictamente topológico para respetar los FOREIGN KEYS
# Se declaran: Archivo origen -> Tabla destino -> Mapeo de columnas -> PKs
ETL_MAPPING = [
    {
        "filename": "records.csv",
        "table": "releases",
        "pk": ["release_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/ocid": "ocid",
            "compiledRelease/date": "date",
            "compiledRelease/language": "language",
        },
    },
    {
        "filename": "parties.csv",
        "table": "parties",
        "pk": ["release_id", "party_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/parties/0/id": "party_id",
            "compiledRelease/parties/0/name": "name",
            "compiledRelease/parties/0/identifier/id": "identifier_id",
            "compiledRelease/parties/0/identifier/scheme": "identifier_scheme",
            "compiledRelease/parties/0/identifier/legalName": "identifier_legal_name",
            "compiledRelease/parties/0/contactPoint/email": "contact_email",
            "compiledRelease/parties/0/contactPoint/name": "contact_name",
            "compiledRelease/parties/0/contactPoint/telephone": "contact_phone",
            "compiledRelease/parties/0/contactPoint/url": "contact_url",
            "compiledRelease/parties/0/contactPoint/faxNumber": "contact_fax",
            "compiledRelease/parties/0/address/countryName": "address_country",
            "compiledRelease/parties/0/address/locality": "address_locality",
            "compiledRelease/parties/0/address/region": "address_region",
            "compiledRelease/parties/0/address/streetAddress": "address_street_address",
            "compiledRelease/parties/0/details/level": "details_level",
            "compiledRelease/parties/0/details/entityType": "details_entity_type",
            "compiledRelease/parties/0/details/type": "details_type",
            "compiledRelease/parties/0/details/scale": "details_scale",
            "compiledRelease/parties/0/details/legalEntityTypeDetail": "details_legal_entity_type_detail",
            "compiledRelease/parties/0/details/activityTypes": "details_activity_types",
        },
    },
    {
        "filename": "parties.csv",
        "table": "party_roles",
        "pk": ["release_id", "party_id", "role"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/parties/0/id": "party_id",
            "compiledRelease/parties/0/roles": "role",
        },
    },
    {
        "filename": "records.csv",
        "table": "tender",
        "pk": ["release_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/tender/id": "tender_id",
            "compiledRelease/tender/title": "title",
            "compiledRelease/tender/status": "status",
            "compiledRelease/tender/submissionMethod": "submission_method",
            "compiledRelease/tender/value/amount": "value_amount",
            "compiledRelease/tender/value/currency": "value_currency",
            "compiledRelease/tender/tenderPeriod/startDate": "tender_period_start_date",
            "compiledRelease/tender/tenderPeriod/endDate": "tender_period_end_date",
            "compiledRelease/tender/tenderPeriod/durationInDays": "duration_in_days",
            "compiledRelease/tender/numberOfTenderers": "number_of_tenderers",
            "compiledRelease/tender/procurementMethod": "procurement_method",
            "compiledRelease/tender/procurementMethodDetails": "procurement_method_details",
            "compiledRelease/tender/mainProcurementCategory": "main_procurement_category",
            "compiledRelease/tender/eligibilityCriteria": "eligibility_criteria",
            "compiledRelease/tender/techniques/hasElectronicAuction": "has_electronic_auction",
        },
    },
    {
        "filename": "ten_tenderers.csv",
        "table": "tenderers",
        "pk": ["release_id", "tenderer_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/tender/tenderers/0/id": "tenderer_id",
            "compiledRelease/tender/tenderers/0/name": "name",
        },
    },
    {
        "filename": "contracts.csv",
        "table": "contracts",
        "pk": ["release_id", "contract_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/contracts/0/id": "contract_id",
            "compiledRelease/contracts/0/awardID": "award_id",
            "compiledRelease/contracts/0/status": "status",
            "compiledRelease/contracts/0/value/amount": "value_amount",
            "compiledRelease/contracts/0/value/currency": "value_currency",
            "compiledRelease/contracts/0/dateSigned": "date_signed",
            "compiledRelease/contracts/0/period/startDate": "period_start_date",
            "compiledRelease/contracts/0/period/endDate": "period_end_date",
            "compiledRelease/contracts/0/period/durationInDays": "duration_in_days",
        },
    },
    {
        "filename": "con_documents.csv",
        "table": "contract_documents",
        "pk": ["release_id", "contract_id", "document_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/contracts/0/id": "contract_id",
            "compiledRelease/contracts/0/documents/0/id": "document_id",
            "compiledRelease/contracts/0/documents/0/documentType": "document_type",
            "compiledRelease/contracts/0/documents/0/documentTypeDetails": "document_type_details",
            "compiledRelease/contracts/0/documents/0/title": "title",
            "compiledRelease/contracts/0/documents/0/url": "url",
            "compiledRelease/contracts/0/documents/0/language": "language",
            "compiledRelease/contracts/0/documents/0/datePublished": "date_published",
        },
    },
    {
        "filename": "con_amendments.csv",
        "table": "contract_amendments",
        "pk": ["release_id", "contract_id", "amendment_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/contracts/0/id": "contract_id",
            "compiledRelease/contracts/0/amendments/0/id": "amendment_id",
            "compiledRelease/contracts/0/amendments/0/date": "date",
            "compiledRelease/contracts/0/amendments/0/description": "description",
            "compiledRelease/contracts/0/amendments/0/amendsAmount/amount": "amends_amount",
            "compiledRelease/contracts/0/amendments/0/amendsAmount/currency": "amends_currency",
            "compiledRelease/contracts/0/amendments/0/rationale": "rationale",
            "compiledRelease/contracts/0/amendments/0/guarantee/type": "guarantee_type",
        },
    },
]


# ============================================================================
# NORMALIZACIÓN DE TIPOS
# ============================================================================
# Columnas BOOLEAN en la DB que viajan como texto en el CSV
BOOLEAN_COLUMNS = {
    "tender": ["has_electronic_auction"],
}
BOOLEAN_VALUES = {"true": True, "false": False, "1": True, "0": False}


def normalize_booleans(table: str, df: pd.DataFrame) -> pd.DataFrame:
    """Columnas BOOLEAN que llegan como texto: '' -> None, 'true'/'false' -> bool."""

    def to_bool(value):
        if value is None or pd.isna(value):
            return None
        return BOOLEAN_VALUES.get(str(value).strip().lower())

    for col in BOOLEAN_COLUMNS.get(table, []):
        if col in df.columns:
            df[col] = [to_bool(v) for v in df[col]]
    return df


# ============================================================================
# CAPA DE SERVICIO (Procesamiento y Transformación)
# ============================================================================
class ETLService:
    def __init__(self, db_repo: DatabaseRepository, chunk_size: int = 50000):
        self.db = db_repo
        self.chunk_size = chunk_size
        self.logger = logging.getLogger("ETL_OCDS")

    @staticmethod
    def calculate_md5(file_path: Path) -> str:
        """Calcula el hash del archivo sin cargarlo todo en RAM."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def process_mapping(self, base_dir: Path, mapping: Dict[str, Any]):
        """Procesa una configuración específica de archivo -> tabla."""
        file_path = base_dir / mapping["filename"]
        # con la carpeta del año (2024/records.csv), si no todos los años se pisan en etl_runs
        nombre = f"{base_dir.name}/{mapping['filename']}"
        table = mapping["table"]
        columns_map = mapping["columns"]
        pks = mapping["pk"]

        if not file_path.exists():
            self.logger.warning(f"Archivo no encontrado: {file_path}")
            return

        file_hash = self.calculate_md5(file_path)

        # Si el archivo exacto ya se procesó, saltamos
        if self.db.check_file_processed(nombre, table, file_hash):
            self.logger.info(f"Saltando {nombre} -> {table} (Ya procesado)")
            return

        self.logger.info(f"Iniciando ingesta: {nombre} -> {table}")

        try:

            headers = pd.read_csv(
                file_path, nrows=0, keep_default_na=False
            ).columns.tolist()

            cols_to_read = [col for col in columns_map.keys() if col in headers]

            if not cols_to_read:
                self.logger.warning(
                    f"Ninguna columna requerida existe en {nombre} para {table}. Saltando."
                )
                self.db.mark_file_processed(nombre, table, file_hash, "SKIPPED")
                return

            chunk_iter = pd.read_csv(
                file_path,
                usecols=cols_to_read,
                chunksize=self.chunk_size,
                dtype=str,
                keep_default_na=False,  # Igual que flatten_adapter (carga por sync)
            )

            total_inserted = 0
            for chunk in chunk_iter:
                # Renombrar columnas del formato largo CSV al formato limpio DB
                chunk = chunk.rename(columns=columns_map)

                if not all(pk in chunk.columns for pk in pks):
                    self.logger.warning(
                        f"Faltan Primary Keys en chunk de {nombre}. Saltando."
                    )
                    continue

                # Eliminar filas con alguna PK nula

                chunk = chunk.dropna(subset=pks, how="any")
                # Descartar filas con PKs vacías (''), dropna solo saca NaN/None
                chunk = chunk[~chunk[pks].eq("").any(axis=1)]

                # Validar que el chunk no quedó vacío tras la limpieza antes de insertar
                if chunk.empty:
                    continue

                # (Aquí agregar validaciones de limpieza de tipos si es necesario)
                if "source_file" not in chunk.columns and table == "releases":
                    chunk["source_file"] = nombre

                if table == "party_roles":
                    # La columna 'role' viene con valores separados por ';'
                    chunk["role"] = chunk["role"].str.split(";")
                    chunk = chunk.explode("role")
                    # Eliminar posibles espacios en blanco alrededor del rol
                    chunk["role"] = chunk["role"].str.strip()
                    chunk["role"] = chunk["role"].replace("", None)
                    chunk = chunk.dropna(subset=["role"])

                chunk = normalize_booleans(table, chunk)

                self.db.bulk_upsert(table, chunk, pks)
                total_inserted += len(chunk)

            self.logger.info(
                f"Éxito: Insertados/Actualizados {total_inserted} registros en {table}"
            )
            self.db.mark_file_processed(nombre, table, file_hash, "SUCCESS")

        except Exception as e:
            self.logger.error(f"Error procesando {nombre} en {table}: {e}")
            # rollback primero, si no Postgres rechaza el insert del FAILED
            self.db.conn.rollback()
            self.db.mark_file_processed(nombre, table, file_hash, "FAILED")
            raise e

    def process_release_dataframes(self, dataframes: dict):
        """
        Procesa e inserta los DataFrames generados por flatten-tool.
        `dataframes` debe tener claves como 'records', 'parties', 'awards', etc.
        """
        try:
            for mapping in ETL_MAPPING:
                table_name = mapping["table"]

                # Buscar el dataframe por el nombre de archivo (sin el .csv)
                source_df_name = mapping["filename"].replace(".csv", "")
                df_original = dataframes.get(source_df_name)

                if df_original is None or df_original.empty:
                    continue

                # Identificar qué columnas necesitamos
                cols_we_need = list(mapping["columns"].keys())

                # Filtrar solo las columnas que existen en este DataFrame
                available_cols = [c for c in cols_we_need if c in df_original.columns]

                # Si el DataFrame no tiene ninguna de las columnas que necesitamos, saltamos
                if not available_cols:
                    continue

                # Copiar y filtrar simulando el 'usecols' del CSV
                df = df_original[available_cols].copy()

                # Renombrar columnas al formato limpio de la DB
                df = df.rename(columns=mapping["columns"])

                # Eliminar filas con PKs nulas
                pk_cols = mapping["pk"]

                # Validación de seguridad: asegurarse de que las PKs existan tras el renombre
                if not all(col in df.columns for col in pk_cols):
                    continue

                df = df.dropna(subset=pk_cols, how="any")
                # Descartar filas con PKs vacías (''), dropna solo saca NaN/None
                df = df[~df[pk_cols].eq("").any(axis=1)]
                if df.empty:
                    continue

                # Tratamiento especial para party_roles
                if table_name == "party_roles" and "role" in df.columns:
                    df["role"] = df["role"].str.split(";")
                    df = df.explode("role")
                    df["role"] = df["role"].str.strip()
                    df["role"] = df["role"].replace("", None)  # party sin rol -> None
                    df = df.dropna(subset=["role"])

                # Para releases añadir marca de origen
                if table_name == "releases" and "source_file" not in df.columns:
                    df["source_file"] = "api_sync"

                df = normalize_booleans(table_name, df)

                self.db.bulk_upsert(table_name, df, pk_cols, commit=False)

            # todas las tablas de este record entran juntas o ninguna
            self.db.conn.commit()

        except Exception as e:
            # rollback si falla para no bloquear la transacción de Postgres
            self.db.conn.rollback()
            self.logger.exception(f"Falla crítica procesando dataframes en memoria")
            raise e


# ============================================================================
# ENTRYPOINT Y ORQUESTACIÓN
# ============================================================================
def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logger = logging.getLogger("ETL_OCDS")

    parser = argparse.ArgumentParser(
        description="ETL Convierte historicos de DNCP a PostgreSQL",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Ruta absoluta o relativa al directorio que contiene los CSV (ej. ./data/2024 o ./data para recursivo)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Busca subcarpetas con formato YYYY dentro de --data-dir y las procesa en orden.",
    )
    parser.add_argument(
        "--year-from", type=int, help="Año mínimo a procesar (inclusive). Ejemplo: 2020"
    )

    parser.add_argument(
        "--year-to", type=int, help="Año máximo a procesar (inclusive). Ejemplo: 2026"
    )
    args = parser.parse_args()

    # db
    DSN = f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}?sslmode={settings.db_sslmode}"

    # csv dir
    base_path = Path(args.data_dir).resolve()

    if not base_path.exists() or not base_path.is_dir():
        logger.error(
            f"El directorio no existe o no es un directorio válido: {base_path}"
        )
        return

    db_repo = DatabaseRepository(DSN)
    etl_service = ETLService(db_repo, chunk_size=50000)

    try:
        if args.recursive:
            logger.info(f"Buscando carpetas YYYY en: ${base_path}")
            # regex para 2010 a 2099
            year_pattern = re.compile(r"^20\d{2}$")

            # Filtramos directorios que cumplen el formato
            year_folders = [
                d
                for d in base_path.iterdir()
                if d.is_dir() and year_pattern.match(d.name)
            ]

            if not year_folders:
                logger.warning(
                    f"No existen carpetas con formato YYYY válido (20XX) en {base_path}"
                )
                return

            # Aplicar filtro de año si se proporcionaron los argumentos
            if args.year_from is not None or args.year_to is not None:
                filtered = []
                for d in year_folders:
                    year = int(d.name)
                    if args.year_from is not None and year < args.year_from:
                        continue
                    if args.year_to is not None and year > args.year_to:
                        continue
                    filtered.append(d)
                year_folders = filtered
                if not year_folders:
                    logger.warning(
                        f"No hay carpetas en el rango {args.year_from}-{args.year_to}"
                    )
                    return

            # ordenamos por fecha mas vieja
            year_folders.sort(key=lambda x: int(x.name))

            for year_dir in year_folders:
                logger.info(
                    f"Procesando archivos para el año: {year_dir.name} {year_dir}"
                )
                for mapping in ETL_MAPPING:
                    etl_service.process_mapping(year_dir, mapping)
                logger.info(f"Año {year_dir.name} procesado correctamente.")
        else:
            logger.info(f"Procesando archivos en: {base_path}")
            for mapping in ETL_MAPPING:
                etl_service.process_mapping(base_path, mapping)
            logger.info(f"Directorio {base_path.name} procesado correctamente.")

        logger.info("Proceso ETL  completado con exito.")

        # Retencion: se deja 1 version por ocid
        borrados = db_repo.prune_all_old_releases()
        logger.info(f"Retencion: {borrados} releases viejos borrados")

        # Refrescar vista materializada de parties (fallback de nombres)
        logger.info("Refrescando party_master...")
        db_repo.refresh_materialized_view("party_master")
        logger.info("party_master refrescado correctamente.")

    except KeyboardInterrupt:
        logger.warning("Proceso interrumpido por el usuario.")
    except Exception as e:
        logger.error(f"Falla crítica en el pipeline: {e}")
    finally:
        db_repo.close()


if __name__ == "__main__":
    main()
