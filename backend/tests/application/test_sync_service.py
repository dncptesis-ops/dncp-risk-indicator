"""Tests de la sincronización incremental.

Cubren la ventana estable (checkpoint - lookback + fecha_hasta como instante
UTC), la deduplicación de ocids, el manejo no abortivo de records corruptos
y la retención de 1 versión por ocid.
"""

import re
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from src.application.sync_service import (
    SYNC_LOOKBACK,
    SyncService,
    _parse_release_date,
)
from src.config import settings

CHECKPOINT = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
FUENTE_TZ = ZoneInfo(settings.source_timezone)


def _record_package(ocid: str, fecha_iso: str) -> dict:
    return {
        "records": [
            {
                "ocid": ocid,
                "compiledRelease": {
                    "id": f"rel-{ocid}",
                    "ocid": ocid,
                    "date": fecha_iso,
                },
            }
        ]
    }


def _client(paginas: list, fechas: dict) -> MagicMock:
    """Fuente falsa: `paginas` son listas de ocids, `fechas` su fecha ISO."""
    client = MagicMock()
    client.search_processes.side_effect = [
        {
            "records": [{"ocid": ocid} for ocid in pagina],
            "pagination": {"total_pages": len(paginas)},
        }
        for pagina in paginas
    ]
    client.get_record.side_effect = lambda ocid: _record_package(ocid, fechas[ocid])
    return client


def _db() -> MagicMock:
    repo = MagicMock()
    repo.start_sync_run.return_value = 7
    repo.get_checkpoint_date.return_value = CHECKPOINT
    repo.prune_old_releases.return_value = 0
    return repo


def _service(client, db, etl=None, **kwargs) -> SyncService:
    return SyncService(
        db_repo=db,
        source_client=client,
        etl_service=etl if etl is not None else MagicMock(),
        start_date="2026-01-01",
        **kwargs,
    )


@patch(
    "src.application.sync_service.record_to_dataframes",
    return_value={"parties": "df"},
)
def test_ventana_usa_lookback_y_fecha_hasta_como_instante_utc(mock_flatten):
    """fecha_desde = checkpoint - lookback; fecha_hasta = ahora, con hora y en UTC."""
    db = _db()
    client = _client([["A"]], {"A": "2026-01-10T11:30:00Z"})
    antes = datetime.now(timezone.utc)

    _service(client, db).sync_once()

    params = client.search_processes.call_args.kwargs
    assert params["fecha_desde"] == (CHECKPOINT - SYNC_LOOKBACK).astimezone(
        FUENTE_TZ
    ).isoformat(timespec="seconds")
    # Instante con hora y offset UTC: nunca un día suelto.
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", params["fecha_hasta"]
    )
    hasta = datetime.fromisoformat(params["fecha_hasta"])
    despues = datetime.now(timezone.utc)
    # "Ahora" con precisión de segundos: ±1 s cubre el truncado de microsegundos.
    assert antes - timedelta(seconds=1) <= hasta <= despues + timedelta(seconds=1)
    # La ventana nunca queda invertida (eso era el 404 con 0 registros).
    assert datetime.fromisoformat(params["fecha_desde"]) < hasta
    assert params["page"] == 1
    # Tamaño de página fijo en el servicio: no depende de ninguna variable.
    assert params["items_per_page"] == 100
    assert client.search_processes.call_count == 1


@patch(
    "src.application.sync_service.record_to_dataframes",
    return_value={"parties": "df"},
)
def test_ocids_duplicados_se_procesan_una_vez(mock_flatten):
    """La ventana solapada re-entrega A: no se vuelve a pedir ni a procesar."""
    db = _db()
    client = _client(
        [["A", "A", "B"]],
        {"A": "2026-01-10T11:00:00Z", "B": "2026-01-10T11:10:00Z"},
    )
    etl = MagicMock()

    procesados = _service(client, db, etl).sync_once()

    assert procesados == 2
    assert client.get_record.call_count == 2
    assert etl.process_release_dataframes.call_count == 2
    # Retención: 1 versión por ocid, con los ocids de la página.
    db.prune_old_releases.assert_called_once_with(["A", "B"])


@patch("src.application.sync_service.record_to_dataframes")
def test_record_corrupto_no_aborta_y_checkpoint_no_pasa_su_fecha(mock_flatten):
    """Un record roto no corta la ejecución y ancla el checkpoint a su fecha."""
    db = _db()
    fechas = {
        "A": "2026-01-10T11:30:00Z",
        "B": "2026-01-10T10:00:00Z",
        "C": "2026-01-10T11:40:00Z",
    }
    client = _client([["A", "B", "C"]], fechas)
    etl = MagicMock()

    def _flatten(record_package):
        if record_package["records"][0]["ocid"] == "B":
            raise ValueError("package corrupto")
        return {"parties": "df"}

    mock_flatten.side_effect = _flatten

    procesados = _service(client, db, etl).sync_once()

    # B falla, pero A y C se cargan y la ejecución se cierra igual.
    assert procesados == 2
    assert etl.process_release_dataframes.call_count == 2
    cierre = db.finish_sync_run.call_args.kwargs
    assert cierre["status"] == "failed"
    assert cierre["records_processed"] == 2
    assert "B" in cierre["error_message"]
    # Checkpoint en la fecha del fallo (10:00), no en la máxima (11:40).
    assert cierre["last_release_date"] == datetime(
        2026, 1, 10, 10, 0, tzinfo=timezone.utc
    )


@patch(
    "src.application.sync_service.record_to_dataframes",
    return_value={"parties": "df"},
)
def test_exito_avanza_checkpoint_a_la_fecha_maxima(mock_flatten):
    """Sin fallos, la paginación se recorre entera y el checkpoint avanza."""
    db = _db()
    client = _client(
        [["A"], ["B"]],
        {"A": "2026-01-10T11:00:00Z", "B": "2026-01-10T11:45:00Z"},
    )

    procesados = _service(client, db).sync_once()

    assert procesados == 2
    assert client.search_processes.call_count == 2
    cierre = db.finish_sync_run.call_args.kwargs
    assert cierre["status"] == "success"
    assert cierre["error_message"] is None
    assert cierre["last_release_date"] == datetime(
        2026, 1, 10, 11, 45, tzinfo=timezone.utc
    )


@patch(
    "src.application.sync_service.record_to_dataframes",
    return_value={"parties": "df"},
)
def test_checkpoint_no_pasa_del_inicio_de_la_ejecucion(mock_flatten):
    """Un record con fecha posterior al inicio no mueve el checkpoint más allá del inicio."""
    db = _db()
    antes = datetime.now(timezone.utc).replace(microsecond=0)
    futura = (antes + timedelta(hours=3)).isoformat()
    client = _client([["A"]], {"A": futura})

    _service(client, db).sync_once()

    despues = datetime.now(timezone.utc)
    cierre = db.finish_sync_run.call_args.kwargs
    assert cierre["status"] == "success"
    assert antes <= cierre["last_release_date"] <= despues
    fecha_hasta = client.search_processes.call_args.kwargs["fecha_hasta"]
    assert cierre["last_release_date"] == datetime.fromisoformat(fecha_hasta)


def test_parse_release_date_tolera_valores_ilegibles():
    """La fecha se parsea sin lanzar: un formato raro no debe romper el sync."""
    assert _parse_release_date("2026-01-10T10:00:00Z") == datetime(
        2026, 1, 10, 10, 0, tzinfo=timezone.utc
    )
    assert _parse_release_date(None) is None
    assert _parse_release_date("") is None
    assert _parse_release_date("no-es-fecha") is None


def test_parse_release_date_sin_offset_se_asume_utc():
    """Un ISO sin offset no debe interpretarse con la zona local del proceso."""
    assert _parse_release_date("2026-01-10T10:00:00") == datetime(
        2026, 1, 10, 10, 0, tzinfo=timezone.utc
    )
    assert _parse_release_date("2026-01-10") == datetime(
        2026, 1, 10, 0, 0, tzinfo=timezone.utc
    )


@patch(
    "src.application.sync_service.record_to_dataframes",
    return_value={"parties": "df"},
)
def test_checkpoint_naive_se_interpreta_como_utc(mock_flatten):
    """Un checkpoint naive de la BD no debe ejecutarse por la zona local.

    El schema usa TIMESTAMPTZ (aware), pero si llegara un valor naive se asume
    UTC en vez de la zona del contenedor.
    """
    db = _db()
    db.get_checkpoint_date.return_value = datetime(2026, 1, 10, 12, 0)  # naive
    client = _client([["A"]], {"A": "2026-01-10T11:30:00Z"})

    _service(client, db).sync_once()

    params = client.search_processes.call_args.kwargs
    assert params["fecha_desde"] == (CHECKPOINT - SYNC_LOOKBACK).astimezone(
        FUENTE_TZ
    ).isoformat(timespec="seconds")
