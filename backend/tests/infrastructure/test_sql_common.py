"""Tests de los fragmentos SQL compartidos por los indicadores (sin base)."""

from datetime import datetime, timezone

from src.infrastructure.async_db.sql_common import ConsultaSQL, nombre_comprador


def test_parametros_se_numeran_en_orden(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.async_db.sql_common.settings.indicators_start_date",
        "2020-01-01",
    )
    q = ConsultaSQL()
    rango = q.rango_valido("f")
    anio = q.anio("f", 2024)
    comprador = q.comprador("r.release_id", "PY-1")
    pagina = q.paginar(10, 20)

    assert "f >= $1 AND f <= NOW()" == rango
    assert "f >= $2 AND f < $3" == anio
    assert "pr.party_id = $4" in comprador
    assert pagina == "LIMIT $5 OFFSET $6"
    assert q.params == [
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        "PY-1",
        10,
        20,
    ]


def test_rango_valido_usa_la_fecha_de_inicio_en_utc(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.async_db.sql_common.settings.indicators_start_date",
        "2010-01-01",
    )
    q = ConsultaSQL()
    q.rango_valido("f")
    assert q.params == [datetime(2010, 1, 1, tzinfo=timezone.utc)]


def test_filtros_opcionales_no_agregan_parametros():
    q = ConsultaSQL()
    assert q.anio("f", None) == "TRUE"
    assert q.comprador("r.release_id", None) == "TRUE"
    assert q.params == []


def test_nombre_comprador_no_tapa_alias_de_la_consulta_externa():
    """La subconsulta no reutiliza el alias p de la consulta externa."""
    sql = nombre_comprador("p.release_id")
    assert "nc_pr.release_id = p.release_id" in sql
    assert " p ON" not in sql and " pm ON" not in sql


def test_ranking_por_entidad_sin_filtro_y_por_unidad_con_filtro():
    """Sin filtro agrupa por buyer; con buyer_id, por procuringEntity."""
    from src.infrastructure.async_db.sql_common import rol_ranking

    assert rol_ranking(None) == "buyer"
    assert rol_ranking("DNCP-SICP-CODE-301") == "procuringEntity"


def test_filtro_de_comprador_usa_solo_el_rol_buyer():
    """El filtro usa solo el rol buyer."""
    sql = ConsultaSQL().comprador("r.release_id", "DNCP-SICP-CODE-301")
    assert "pr.role = 'buyer'" in sql
    assert "procuringEntity" not in sql
