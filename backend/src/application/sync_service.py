import logging
import resource
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from src.config import settings
from src.etl.flatten_adapter import record_to_dataframes
from src.etl.ocds_flatten_ingest import ETLService
from src.infrastructure.database import DatabaseRepository

logger = logging.getLogger(__name__)

# La fuente publica con retraso: se re-consulta una ventana hacia atras desde
# el checkpoint para no perder releases publicados tarde.
SYNC_LOOKBACK = timedelta(minutes=60)


def _rss_mb() -> float:
    """RSS máximo del proceso en MiB (portable Linux/macOS)."""
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        rss = rss * 1024  # en Linux ru_maxrss viene en KiB
    return rss / (1024 * 1024)


def _children_rss_mb() -> float:
    """RSS máximo acumulado de procesos hijos (p. ej. flatten-tool) en MiB."""
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    if sys.platform != "darwin":
        rss = rss * 1024
    return rss / (1024 * 1024)


def _as_utc(value: datetime) -> datetime:
    """Pasa a UTC. Si viene sin zona se toma como UTC (no la zona de la máquina)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_release_date(value) -> datetime | None:
    """Fecha del release en UTC, o None si viene vacía o mal formada."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        logger.warning(f"Fecha de release ilegible: {value!r}")
        return None
    return _as_utc(parsed)


class SyncService:
    def __init__(
        self,
        db_repo: DatabaseRepository,
        source_client,  # cualquier adaptador con search_processes() y get_record()
        etl_service: ETLService = None,
        start_date: str = None,
        items_per_page: int = 100,
    ):
        self.db_repo = db_repo
        self.source_client = source_client
        self.etl_service = etl_service or ETLService(db_repo)
        self.default_start_date = start_date or settings.default_start_date
        self.items_per_page = items_per_page

    def _get_checkpoint_date(self) -> datetime:
        last_checkpoint = self.db_repo.get_checkpoint_date()
        if last_checkpoint:
            return _as_utc(last_checkpoint)
        max_release = self.db_repo.get_max_release_date()
        if max_release:
            return _as_utc(max_release)
        return datetime.fromisoformat(self.default_start_date).replace(
            tzinfo=ZoneInfo(settings.source_timezone)
        )

    def _iter_records_concurrently(self, ocids: list):
        """Obtiene los record packages en paralelo con una ventana acotada a
        max_workers y entrega (ocid, record_package) apenas cada future termina,
        sin acumular todos los records de la página en RAM."""
        pending = {}
        with ThreadPoolExecutor(
            max_workers=settings.sync_max_concurrent_requests
        ) as pool:
            ocids_iter = iter(ocids)

            def _submit(ocid):
                pending[pool.submit(self.source_client.get_record, ocid)] = ocid

            # Llenar la ventana inicial (hasta max_workers)
            for _ in range(settings.sync_max_concurrent_requests):
                try:
                    _submit(next(ocids_iter))
                except StopIteration:
                    break

            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    ocid = pending.pop(future)
                    # Mantener la ventana llena con el siguiente ocid
                    try:
                        _submit(next(ocids_iter))
                    except StopIteration:
                        pass
                    try:
                        record_package = future.result()
                    except Exception as e:
                        logger.error(f"Error al obtener record {ocid}: {e}")
                        record_package = None
                    yield ocid, record_package

    def sync_once(self):
        """Ejecuta una sincronización completa y registra en sync_log."""
        source_tz = ZoneInfo(settings.source_timezone)
        run_id = self.db_repo.start_sync_run()
        checkpoint = self._get_checkpoint_date()
        window_start = checkpoint - SYNC_LOOKBACK

        techo = datetime.now(timezone.utc).replace(microsecond=0)
        fecha_hasta = techo.isoformat(timespec="seconds")
        logger.info(
            f"Iniciando sincronización (run_id={run_id}) de "
            f"{window_start.astimezone(source_tz).isoformat(timespec='seconds')} "
            f"a {fecha_hasta}"
        )

        page = 1
        total_records_processed = 0
        last_processed_date = None
        failed_ocids = []
        fechas_fallidas = {}
        vistos = set()
        status = "success"
        error_message = None
        try:
            while True:
                fecha_desde = window_start.astimezone(source_tz).isoformat(
                    timespec="seconds"
                )
                response = self.source_client.search_processes(
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                    page=page,
                    items_per_page=self.items_per_page,
                )
                records = response.get("records", [])
                if not records:
                    logger.info("No se encontraron más records.")
                    break

                ocids = []
                for r in records:
                    ocid = r.get("ocid")
                    if not ocid or ocid in vistos:
                        continue
                    vistos.add(ocid)
                    ocids.append(ocid)
                logger.info(
                    f"Página {page}: {len(ocids)} ocids | RSS proc={_rss_mb():.1f} MiB hijos={_children_rss_mb():.1f} MiB"
                )

                for ocid, record_package in self._iter_records_concurrently(ocids):
                    if record_package is None:
                        failed_ocids.append(ocid)
                        continue
                    # Se inicializa fuera del try: si el paquete viene malformado,
                    # el bloque except necesita la variable ya definida.
                    fecha = None
                    try:
                        logger.info(f"Procesando {ocid} | RSS proc={_rss_mb():.1f} MiB")
                        # Extraemos la fecha antes de enviar a record_to_dataframes
                        # porque flatten_adapter.py vaciará el diccionario de la memoria
                        # CRÍTICO: NO guardar referencias a diccionarios internos, solo el string.
                        pkg_cr = record_package["records"][0]["compiledRelease"]
                        release_date_str = pkg_cr.get("date")
                        # se parsea antes del ETL por si falla
                        fecha = _parse_release_date(release_date_str)
                        # el checkpoint no pasa de techo: lo publicado despues todavia no se pidio
                        if fecha is not None and fecha > techo:
                            fecha = techo

                        dataframes = record_to_dataframes(record_package)
                        logger.info(
                            f"flatten OK {ocid} | RSS proc={_rss_mb():.1f} MiB hijos={_children_rss_mb():.1f} MiB"
                        )
                        self.etl_service.process_release_dataframes(dataframes)
                        total_records_processed += 1

                        if fecha is not None and (
                            last_processed_date is None or fecha > last_processed_date
                        ):
                            last_processed_date = fecha
                    except Exception as e:
                        logger.error(
                            f"Error procesando record {ocid}: {e}", exc_info=True
                        )
                        failed_ocids.append(ocid)
                        # Un record corrupto no corta la ejecución:
                        # el checkpoint no avanza mas alla de su fecha.
                        fechas_fallidas[ocid] = fecha

                # Retencion: la base guarda el estado actual (1 version por
                # ocid), no el historial de versiones recompiladas.
                borrados = self.db_repo.prune_old_releases(ocids)
                if borrados:
                    logger.info(f"Retencion: {borrados} releases borrados")

                pagination = response.get("pagination", {})
                total_pages = pagination.get("total_pages", 1)

                self.db_repo.update_sync_progress(
                    run_id=run_id,
                    last_release_date=(
                        last_processed_date if total_records_processed > 0 else None
                    ),
                    records_processed=total_records_processed,
                )
                logger.info(
                    f"Página {page}/{total_pages} OK — {total_records_processed} records acumulados"
                )

                if page >= total_pages:
                    break
                page += 1

            logger.info(
                f"Sincronización completada. {total_records_processed} records."
            )
            if failed_ocids:
                status = "failed"
                fechas = [f for f in fechas_fallidas.values() if f]
                last_processed_date = min(fechas) if fechas else window_start
                error_message = (
                    f"{len(failed_ocids)} records con error: " f"{failed_ocids[:10]}"
                )
                logger.warning(error_message)

        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(f"Sincronización fallida: {e}")

        try:
            self.db_repo.finish_sync_run(
                run_id=run_id,
                status=status,
                records_processed=total_records_processed,
                last_release_date=(
                    last_processed_date if total_records_processed > 0 else None
                ),
                error_message=error_message,
            )
        except Exception as e:
            logger.error(f"No se pudo cerrar sync_log run_id={run_id}: {e}")

        return total_records_processed
