import json
import logging
import shutil
import subprocess
from pathlib import Path
import tempfile
from typing import Dict
import pandas as pd
from src.config import settings

logger = logging.getLogger(__name__)

FLATTEN_TIMEOUT_SECONDS = 900  # 15 min


def record_to_dataframes(record_package: dict) -> Dict[str, pd.DataFrame]:
    if settings.debug_flatten_output:
        output_dir = Path(settings.debug_flatten_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"debug: archivos en {output_dir}")
    else:
        output_dir = Path(tempfile.mkdtemp())

    input_json = output_dir / "record_package.json"
    with input_json.open("w", encoding="utf-8") as f:
        json.dump(record_package, f, ensure_ascii=False)

    # Limpiar CSVs previos para no mezclar records distintos
    # (produce FK violations por datos stale, p. ej. contracts.csv de un
    #  record con con_amendments.csv de otro).
    flattened_dir = output_dir / "flattened"
    if flattened_dir.exists():
        shutil.rmtree(flattened_dir)

    # Vaciamos el diccionario y forzamos el recolector de basura antes del subprocess para
    # liberar memoria y evitar error OOM (Out Of Memory)
    record_package.clear()
    import gc
    gc.collect()

    cmd = [
        "flatten-tool",
        "flatten",
        "record_package.json",
        "--root-id=ocid",
        "--main-sheet-name=records",
        "--root-list-path=records",
        "--output-format",
        "csv",
    ]
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            cwd=str(output_dir),
            timeout=FLATTEN_TIMEOUT_SECONDS,  # si flatten-tool cuelga, abortamos en vez de esperar para siempre
        )
    except subprocess.TimeoutExpired:
        logger.error(
            f"flatten-tool excedió {FLATTEN_TIMEOUT_SECONDS}s en {output_dir}"
        )
        raise

    # Renombramos archivos que tengan prefijo "com_" para que coincidan con el mapeo histórico(procesos_completos)
    # Hay un limite de 31 caracteres para los nombres de las hojas de excel que luego se convierten a csv
    # al alcanzar el limite. la palabra clave compiledRelease se corta a com_, tender a ten_
    for csv_file in flattened_dir.glob("com_*.csv"):
        new_name = csv_file.name.replace("com_", "")
        csv_file.rename(flattened_dir / new_name)

    # Solo cargamos las hojas que declara el ETL_MAPPING: flatten-tool escribe
    # un CSV por cada lista anidada de OCDS (~60) y usamos ~8, así que cargar
    # todas cuesta RAM y I/O (y algunos CSV son enormes). Import local para no
    # acoplar los módulos en tiempo de import.
    from src.etl.ocds_flatten_ingest import ETL_MAPPING

    needed_stems = {m["filename"].replace(".csv", "") for m in ETL_MAPPING}

    # leemos los CSV
    dataframes = {}
    for csv_path in flattened_dir.glob("*.csv"):
        stem = csv_path.stem  # "records", "parties", "ten_tenderers", ...
        if stem not in needed_stems:
            continue
        df = pd.read_csv(csv_path, keep_default_na=False, dtype=str)
        if not df.empty:
            dataframes[stem] = df

    # en prod rm tmp files
    if not settings.debug_flatten_output:
        shutil.rmtree(output_dir, ignore_errors=True)

    return dataframes
