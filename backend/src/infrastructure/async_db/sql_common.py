"""Partes SQL comunes a R018, R063 y R064.

- Se parte de latest_releases (una fila por proceso).
- Solo cuentan fechas entre INDICATORS_START_DATE y hoy.
- El CTE procesos es MATERIALIZED: sin eso los listados con ORDER BY + LIMIT
  hacen un nested loop contra la vista y tardan mucho.
"""

from datetime import datetime, timezone

from src.config import settings

SIN_NOMBRE_ENTIDAD = "Entidad sin denominación en SICP"
SIN_NOMBRE_PROVEEDOR = "Proveedor sin denominación en SICP"

# buyer: la entidad que paga. procuringEntity: la unidad que hace la compra.
# Se usa un solo rol a la vez para no contar dos veces el mismo proceso.
ROL_ENTIDAD = "buyer"
ROL_UNIDAD = "procuringEntity"
AGRUPACION = {ROL_ENTIDAD: "buyer", ROL_UNIDAD: "procuring_entity"}


def rol_ranking(buyer_id: str | None) -> str:
    """Sin filtro se agrupa por buyer; con una entidad elegida, por sus unidades."""
    return ROL_UNIDAD if buyer_id is not None else ROL_ENTIDAD

# Fecha de referencia de cada tipo de caso (alias t = tender, c = contracts).
FECHA_LICITACION = "COALESCE(t.tender_period_end_date, t.tender_period_start_date)"
FECHA_CONTRATO = "COALESCE(c.date_signed, c.period_start_date)"


def fecha_inicio_indicadores() -> datetime:
    """`INDICATORS_START_DATE` como instante UTC."""
    return datetime.fromisoformat(settings.indicators_start_date).replace(
        tzinfo=timezone.utc
    )


def porcentaje(parte: str, total: str) -> str:
    """Expresión SQL del porcentaje con un decimal (NULL si el total es 0)."""
    return f"ROUND(100.0 * {parte} / NULLIF({total}, 0), 1)"


def nombre_comprador(release_sql: str) -> str:
    """Nombre del buyer del proceso; si falta, el de party_master."""
    # alias nc_* para no repetir los alias de la consulta que la usa
    return f"""COALESCE(
        (SELECT COALESCE(nc_p.name, nc_pm.name)
         FROM party_roles nc_pr
         LEFT JOIN parties nc_p
             ON nc_p.release_id = nc_pr.release_id AND nc_p.party_id = nc_pr.party_id
         LEFT JOIN party_master nc_pm ON nc_pm.party_id = nc_pr.party_id
         WHERE nc_pr.release_id = {release_sql}
           AND nc_pr.role = '{ROL_ENTIDAD}'
         ORDER BY COALESCE(nc_p.name, nc_pm.name) IS NULL, nc_pr.party_id
         LIMIT 1),
        '{SIN_NOMBRE_ENTIDAD}'
    )"""


def a_float(valor) -> float:
    """Porcentaje de la base (NUMERIC o NULL) como float."""
    return float(valor) if valor is not None else 0.0


def contratos_marcados(row) -> list[dict]:
    """Contratos marcados de un proceso (R063, R064): código y award_id."""
    return [
        {"contract_id": cid, "award_id": aid}
        for cid, aid in zip(row["marcados_id"], row["marcados_award"])
    ]


class ConsultaSQL:
    """Arma partes de la consulta y junta los parámetros ($1, $2, ...)."""

    def __init__(self):
        self.params: list = []

    def param(self, valor) -> str:
        self.params.append(valor)
        return f"${len(self.params)}"

    def rango_valido(self, fecha_sql: str) -> str:
        """Fecha entre el inicio configurado y hoy."""
        desde = self.param(fecha_inicio_indicadores())
        return f"{fecha_sql} >= {desde} AND {fecha_sql} <= NOW()"

    def anio(self, fecha_sql: str, year: int | None) -> str:
        if year is None:
            return "TRUE"
        desde = self.param(datetime(year, 1, 1, tzinfo=timezone.utc))
        hasta = self.param(datetime(year + 1, 1, 1, tzinfo=timezone.utc))
        return f"{fecha_sql} >= {desde} AND {fecha_sql} < {hasta}"

    def comprador(self, release_sql: str, buyer_id: str | None) -> str:
        """Procesos cuya entidad compradora (buyer) es `buyer_id`."""
        if buyer_id is None:
            return "TRUE"
        return f"""{release_sql} IN (
            SELECT pr.release_id
            FROM party_roles pr
            WHERE pr.role = '{ROL_ENTIDAD}'
              AND pr.party_id = {self.param(buyer_id)}
        )"""

    def paginar(self, limit: int, offset: int) -> str:
        return f"LIMIT {self.param(limit)} OFFSET {self.param(offset)}"
