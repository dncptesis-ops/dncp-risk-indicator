"""Pruebas con datos controlados: CSV armados a mano -> ETL -> PostgreSQL -> API.

Los resultados esperados están calculados a mano en datos_controlados.py. Si una
consulta de los indicadores cambia y deja de dar esos valores, estas pruebas fallan.
"""

import asyncio

import asyncpg
import httpx
import psycopg2
import pytest

from src.interfaces.api.dependencies import get_pool
from src.interfaces.api.main import app
from src.interfaces.api.routers.common import invalidate_common_cache
from tests.integration.conftest import cargar_csvs
from tests.integration.datos_controlados import ENTIDAD, RESULTADOS_ESPERADOS as E

pytestmark = pytest.mark.usefixtures("datos_cargados")

CAMPOS_KPI = {
    "r018": ("total_competitive", "r018_count", "r018_percentage"),
    "r063": ("total_processes", "r063_count", "r063_percentage"),
    "r064": ("total_processes", "r064_count", "r064_percentage"),
}


def consultar(dsn: str, ruta: str) -> dict:
    """GET a la API real, con el pool apuntando a la base de prueba."""

    async def _get():
        pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=2)
        app.dependency_overrides[get_pool] = lambda: pool
        invalidate_common_cache()
        try:
            transporte = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transporte, base_url="http://prueba") as c:
                r = await c.get(ruta)
        finally:
            app.dependency_overrides.pop(get_pool, None)
            await pool.close()
        assert r.status_code == 200, (ruta, r.status_code, r.text)
        return r.json()

    return asyncio.run(_get())


def kpi(dsn, indicador, filtros=""):
    datos = consultar(dsn, f"/{indicador}/kpi{filtros}")
    total, marcados, pct = CAMPOS_KPI[indicador]
    return {"total": datos[total], "marcados": datos[marcados], "porcentaje": datos[pct]}


def contar(dsn, sql):
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


@pytest.fixture
def dsn(datos_cargados):
    return datos_cargados["dsn"]


# --- Carga -------------------------------------------------------------------

def test_la_carga_deja_una_version_por_proceso_y_registra_los_archivos(dsn):
    assert contar(dsn, "SELECT count(*), count(DISTINCT ocid) FROM releases") == [(21, 21)]
    assert contar(dsn, "SELECT release_id FROM releases WHERE ocid = 'ocds-prueba-T8'") == [("T8-r2",)]
    archivos = contar(dsn, "SELECT file_name FROM etl_runs WHERE status = 'SUCCESS' ORDER BY 1")
    assert len(archivos) == 8 and all(f.startswith("2024/") for (f,) in archivos)


def test_volver_a_cargar_los_mismos_csv_no_cambia_nada(datos_cargados, dsn):
    antes = contar(dsn, "SELECT count(*) FROM releases UNION ALL SELECT count(*) FROM contracts "
                        "UNION ALL SELECT count(*) FROM contract_amendments")
    cargar_csvs(dsn, datos_cargados["carpeta"])
    despues = contar(dsn, "SELECT count(*) FROM releases UNION ALL SELECT count(*) FROM contracts "
                          "UNION ALL SELECT count(*) FROM contract_amendments")
    assert antes == despues


# --- R018 ----------------------------------------------------------------------

def test_r018_kpi(dsn):
    assert kpi(dsn, "r018") == E["r018"]
    assert kpi(dsn, "r018", "?year=2024") == E["r018_2024"]
    assert kpi(dsn, "r018", "?year=2025") == E["r018_2025"]
    assert kpi(dsn, "r018", "?proc_method=selective") == E["r018_selective"]


def test_r018_serie_mensual_suma_lo_mismo_que_el_kpi(dsn):
    meses = consultar(dsn, "/r018/monthly")["data"]
    assert [(m["month"], m["total"], m["r018_count"]) for m in meses] == E["r018_meses"]
    assert sum(m["r018_count"] for m in meses) == E["r018"]["marcados"]


def test_r018_ranking_por_entidad_y_desglose_por_unidad(dsn):
    ranking = consultar(dsn, "/r018/top-entities")
    assert ranking["group_by"] == "buyer"
    assert [(f["entity_id"], f["r018_count"]) for f in ranking["data"]] == [
        (ENTIDAD["A"][0], 1), (ENTIDAD["B"][0], 1)
    ]
    desglose = consultar(dsn, f"/r018/top-entities?buyer_id={ENTIDAD['A'][0]}")
    assert desglose["group_by"] == "procuring_entity"
    assert [(f["entity_id"], f["r018_count"]) for f in desglose["data"]] == [(ENTIDAD["A"][2], 1)]


def test_r018_proveedores_y_listado(dsn):
    proveedores = consultar(dsn, "/r018/suppliers")["data"]
    assert [(p["tenderer_id"], p["ruc"], p["sole_bidder_count"]) for p in proveedores] == [
        ("PY-RUC-80000001-1", "80000001-1", 2)
    ]
    listado = consultar(dsn, "/r018/tenders?limit=50")
    assert listado["total_count"] == E["r018"]["marcados"]
    assert sorted(t["ocid"] for t in listado["data"]) == ["ocds-prueba-T1", "ocds-prueba-T3"]


# --- R063 ----------------------------------------------------------------------

def test_r063_kpi(dsn):
    assert kpi(dsn, "r063") == E["r063"]
    assert kpi(dsn, "r063", "?year=2024") == E["r063_2024"]
    assert kpi(dsn, "r063", "?year=2025") == E["r063_2025"]
    assert kpi(dsn, "r063", f"?buyer_id={ENTIDAD['A'][0]}") == E["r063_entidad_A"]
    assert kpi(dsn, "r063", f"?buyer_id={ENTIDAD['B'][0]}") == E["r063_entidad_B"]


def test_r063_listado_cuenta_cada_proceso_una_vez(dsn):
    listado = consultar(dsn, "/r063/processes?limit=50")
    assert listado["total_count"] == E["r063"]["marcados"]
    por_ocid = {p["ocid"]: p for p in listado["data"]}
    assert sorted(por_ocid) == ["ocds-prueba-C2", "ocds-prueba-C3", "ocds-prueba-C5"]
    assert (por_ocid["ocds-prueba-C2"]["active_contracts"], por_ocid["ocds-prueba-C2"]["unsigned_contracts"]) == (2, 1)
    # de los dos contratos de C2 solo C2-k2 no tiene el documento
    assert por_ocid["ocds-prueba-C2"]["flagged_contracts"] == [
        {"contract_id": "C2-k2", "award_id": "award-C2-k2"}
    ]


def test_r063_serie_mensual_suma_lo_mismo_que_el_kpi(dsn):
    meses = consultar(dsn, "/r063/monthly")["data"]
    assert sum(m["total"] for m in meses) == E["r063"]["total"]
    assert sum(m["r063_count"] for m in meses) == E["r063"]["marcados"]


# --- R064 ----------------------------------------------------------------------

def test_r064_kpi(dsn):
    assert kpi(dsn, "r064") == E["r064"]
    assert kpi(dsn, "r064", "?year=2024") == E["r064_2024"]
    assert kpi(dsn, "r064", "?year=2025") == E["r064_2025"]
    assert kpi(dsn, "r064", f"?buyer_id={ENTIDAD['A'][0]}") == E["r064_entidad_A"]
    assert kpi(dsn, "r064", f"?buyer_id={ENTIDAD['B'][0]}") == E["r064_entidad_B"]


def test_r064_listado_con_rescision_y_varios_contratos(dsn):
    listado = consultar(dsn, "/r064/processes?limit=50")
    assert listado["total_count"] == E["r064"]["marcados"]
    por_ocid = {p["ocid"]: p for p in listado["data"]}
    assert sorted(por_ocid) == ["ocds-prueba-M1", "ocds-prueba-M2", "ocds-prueba-M5"]
    m5 = por_ocid["ocds-prueba-M5"]
    assert (m5["contracts"], m5["amended_contracts"], m5["amendment_count"]) == (2, 2, 3)
    assert m5["first_amendment_date"].startswith("2024-09-01")
    assert [c["contract_id"] for c in m5["flagged_contracts"]] == ["M5-k1", "M5-k2"]
    assert [c["contract_id"] for c in por_ocid["ocds-prueba-M2"]["flagged_contracts"]] == ["M2-k1"]


def test_r064_ranking_suma_lo_mismo_que_el_kpi(dsn):
    ranking = consultar(dsn, "/r064/top-entities")["data"]
    assert sum(f["r064_count"] for f in ranking) == E["r064"]["marcados"]


# --- Catálogos -------------------------------------------------------------------

def test_catalogos_de_la_api(dsn):
    assert consultar(dsn, "/common/years")["years"] == [2025, 2024]
    compradores = consultar(dsn, "/common/buyers")["data"]
    assert sorted(b["buyer_id"] for b in compradores) == [ENTIDAD["A"][0], ENTIDAD["B"][0]]
    assert consultar(dsn, "/common/status")["updated_at"].startswith("2025-03-02T14:00:00")
