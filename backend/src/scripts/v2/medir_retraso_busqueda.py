"""
Mide cuánto tarda un proceso en aparecer en /search/processes después de su fecha.

Cada --intervalo minutos pide las últimas horas y anota la primera vez que ve cada
proceso (ocid + fecha de su última release). Solo se mide lo que tiene fecha
posterior al arranque del script: lo anterior ya estaba en la búsqueda.

El retraso de cada proceso queda entre dos valores: desde la consulta anterior en
la que todavía no estaba hasta la consulta en la que apareció.

Uso (desde backend/):

    uv run python -m src.scripts.v2.medir_retraso_busqueda --horas 8
    uv run python -m src.scripts.v2.medir_retraso_busqueda --resumen data/retraso_busqueda.csv

Para que la Mac no se duerma mientras mide:

    caffeinate -i uv run python -m src.scripts.v2.medir_retraso_busqueda --horas 8
"""

import argparse
import csv
import logging
import math
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.sync_service import SYNC_LOOKBACK
from src.infrastructure.dncp_client import DNCPClient

logger = logging.getLogger("medir_retraso")

COLUMNAS = ["ocid", "fecha_release", "consulta_anterior", "visto", "retraso_min", "retraso_max"]


def _utc(texto):
    return datetime.fromisoformat(texto).astimezone(timezone.utc)


def _minutos(delta):
    return round(delta.total_seconds() / 60, 1)


def buscar(client, desde, hasta):
    """Todos los (ocid, fecha) de la ventana, recorriendo las páginas."""
    vistos, page = {}, 1
    while True:
        resp = client.search_processes(
            fecha_desde=desde.isoformat(timespec="seconds"),
            fecha_hasta=hasta.isoformat(timespec="seconds"),
            page=page,
            items_per_page=1000,
        )
        for rec in resp.get("records", []):
            fecha = (rec.get("compiledRelease") or {}).get("date")
            if fecha:
                vistos[(rec["ocid"], fecha)] = _utc(fecha)
        if page >= resp.get("pagination", {}).get("total_pages", 1):
            return vistos
        page += 1


def medir(horas, intervalo, ventana, salida):
    client = DNCPClient()
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
    fin = (inicio + timedelta(hours=horas)).replace(microsecond=0)
    ya_vistos = set()
    anterior = None
    nuevos_total = 0

    salida.parent.mkdir(parents=True, exist_ok=True)
    nuevo_archivo = not salida.exists()
    with salida.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo_archivo:
            w.writerow(COLUMNAS)
        logger.info(f"Midiendo de {inicio.isoformat()} a {fin.isoformat()}, cada {intervalo} min")

        while True:
            ahora = datetime.now(timezone.utc).replace(microsecond=0)
            try:
                vistos = buscar(client, ahora - timedelta(hours=ventana), ahora + timedelta(hours=1))
            except Exception as e:  # un fallo de red no corta la medicion
                logger.error(f"Consulta fallida: {e}")
                vistos = None

            if vistos is not None:
                nuevos = 0
                for (ocid, texto), fecha in sorted(vistos.items(), key=lambda x: x[1]):
                    if (ocid, texto) in ya_vistos:
                        continue
                    ya_vistos.add((ocid, texto))
                    # lo que tiene fecha anterior al arranque ya estaba publicado
                    if anterior is None or fecha < inicio:
                        continue
                    minimo = max(timedelta(0), anterior - fecha)
                    w.writerow([ocid, fecha.isoformat(), anterior.isoformat(), ahora.isoformat(),
                                _minutos(minimo), _minutos(ahora - fecha)])
                    nuevos += 1
                f.flush()
                nuevos_total += nuevos
                logger.info(f"{ahora.isoformat()}: {len(vistos)} en la ventana, {nuevos} nuevos medidos")
                anterior = ahora

            if ahora >= fin:
                break
            time.sleep(intervalo * 60)

    logger.info(f"Fin. Procesos medidos: {nuevos_total}. Archivo: {salida}")


def resumen(salida):
    with salida.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        print("Todavía no hay procesos medidos.")
        return
    maximos = sorted(float(r["retraso_max"]) for r in filas)
    minimos = [float(r["retraso_min"]) for r in filas]
    limite = _minutos(SYNC_LOOKBACK)
    percentil_90 = maximos[math.ceil(len(maximos) * 0.9) - 1]
    print(f"Procesos medidos: {len(filas)}")
    print(f"Retraso (cota superior): mediana {statistics.median(maximos)} min, "
          f"p90 {percentil_90} min, máximo {maximos[-1]} min")
    print(f"Retraso (cota inferior) máximo: {max(minimos)} min")
    print(f"Con retraso seguro mayor a SYNC_LOOKBACK ({limite} min): "
          f"{sum(m > limite for m in minimos)}")


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.getLogger("src.infrastructure.dncp_client").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--horas", type=float, default=8, help="cuánto tiempo medir")
    parser.add_argument("--intervalo", type=float, default=5, help="minutos entre consultas")
    parser.add_argument("--ventana", type=float, default=6, help="horas hacia atrás de cada consulta")
    parser.add_argument("--salida", type=Path, default=Path("data/retraso_busqueda.csv"))
    parser.add_argument("--resumen", type=Path, help="solo muestra el resumen de un CSV ya medido")
    args = parser.parse_args(argv)

    if args.resumen:
        resumen(args.resumen)
        return 0
    try:
        medir(args.horas, args.intervalo, args.ventana, args.salida)
    except KeyboardInterrupt:
        logger.info("Cortado a mano.")
    resumen(args.salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
