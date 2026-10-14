import asyncpg
from typing import Dict, Any
from src.core.ports.r064_repository import R064Repository
from src.infrastructure.async_db.sql_common import (
    FECHA_CONTRATO,
    AGRUPACION,
    SIN_NOMBRE_ENTIDAD,
    ConsultaSQL,
    a_float,
    contratos_marcados,
    nombre_comprador,
    porcentaje,
    rol_ranking,
)

# contrato con al menos una enmienda
MARCADO = "amended_contracts > 0"


class AsyncpgR064Repository(R064Repository):
    """R064: contrato con modificaciones (OCP 2024).

    Procesos con contratos active o terminated (solo un contrato firmado puede
    tener enmiendas); se marca si alguno tiene enmiendas. La fecha es la del
    primer contrato.
    """

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    @staticmethod
    def _procesos(q: ConsultaSQL, year: int | None, buyer_id: str | None) -> str:
        """CTE procesos: una fila por proceso con contratos firmados."""
        return f"""enmiendas AS (
            SELECT release_id, contract_id, COUNT(*) AS cantidad, MIN(date) AS primera
            FROM contract_amendments
            GROUP BY release_id, contract_id
        ),
        contratos AS (
            SELECT
                r.release_id,
                r.ocid,
                c.contract_id,
                c.award_id,
                {FECHA_CONTRATO} AS fecha,
                COALESCE(e.cantidad, 0) AS enmiendas,
                e.primera
            FROM latest_releases r
            JOIN contracts c ON c.release_id = r.release_id
            LEFT JOIN enmiendas e
                ON e.release_id = c.release_id AND e.contract_id = c.contract_id
            WHERE c.status IN ('active', 'terminated')
              AND {q.rango_valido(FECHA_CONTRATO)}
              AND {q.comprador("r.release_id", buyer_id)}
        ),
        procesos AS MATERIALIZED (
            SELECT
                release_id,
                ocid,
                MIN(fecha) AS fecha,
                COUNT(*) AS contracts,
                COUNT(*) FILTER (WHERE enmiendas > 0) AS amended_contracts,
                SUM(enmiendas) AS amendment_count,
                MIN(primera) AS first_amendment_date,
                -- los contratos marcados, para enlazar a su ficha en el portal
                ARRAY_AGG(contract_id ORDER BY contract_id) FILTER (WHERE enmiendas > 0) AS marcados_id,
                ARRAY_AGG(award_id ORDER BY contract_id) FILTER (WHERE enmiendas > 0) AS marcados_award
            FROM contratos
            GROUP BY release_id, ocid
            HAVING {q.anio("MIN(fecha)", year)}
        )"""

    async def get_r064_data(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> Dict[str, Any]:
        q = ConsultaSQL()
        query = f"""
        WITH {self._procesos(q, year, buyer_id)}
        SELECT
            COUNT(*) AS total_processes,
            COUNT(*) FILTER (WHERE {MARCADO}) AS r064_count,
            {porcentaje(f"COUNT(*) FILTER (WHERE {MARCADO})", "COUNT(*)")} AS r064_percentage
        FROM procesos;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *q.params)

        return {
            "total_processes": row["total_processes"],
            "r064_count": row["r064_count"],
            "r064_percentage": a_float(row["r064_percentage"]),
        }

    async def get_r064_time_series(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        q = ConsultaSQL()
        query = f"""
        WITH {self._procesos(q, year, buyer_id)}
        SELECT
            TO_CHAR(DATE_TRUNC('month', fecha), 'YYYY-MM') AS month,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE {MARCADO}) AS r064_count,
            {porcentaje(f"COUNT(*) FILTER (WHERE {MARCADO})", "COUNT(*)")} AS r064_percentage
        FROM procesos
        GROUP BY DATE_TRUNC('month', fecha)
        ORDER BY DATE_TRUNC('month', fecha);
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *q.params)

        return [
            {
                "month": row["month"],
                "total": row["total"],
                "r064_count": row["r064_count"],
                "r064_percentage": a_float(row["r064_percentage"]),
            }
            for row in rows
        ]

    async def get_r064_top_entities(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        q = ConsultaSQL()
        procesos = self._procesos(q, year, buyer_id)
        # sin filtro agrupa por buyer; con buyer_id, por sus unidades
        rol = rol_ranking(buyer_id)
        query = f"""
        WITH {procesos},
        por_entidad AS (
            SELECT
                pr.party_id AS entity_id,
                MAX(p.release_id) AS sample_release_id,
                COUNT(DISTINCT p.release_id) AS total_processes,
                COUNT(DISTINCT p.release_id) FILTER (WHERE p.{MARCADO}) AS r064_count
            FROM procesos p
            JOIN party_roles pr
                ON pr.release_id = p.release_id
                AND pr.role = '{rol}'
            GROUP BY pr.party_id
            HAVING COUNT(DISTINCT p.release_id) FILTER (WHERE p.{MARCADO}) > 0
        ),
        pagina AS (
            SELECT *, COUNT(*) OVER () AS total_count
            FROM por_entidad
            ORDER BY r064_count DESC, entity_id
            {q.paginar(limit, offset)}
        )
        SELECT
            COALESCE(pa.name, pm.name, '{SIN_NOMBRE_ENTIDAD}') AS entity,
            g.entity_id,
            g.total_processes,
            g.r064_count,
            {porcentaje("g.r064_count", "g.total_processes")} AS r064_percentage,
            g.total_count
        FROM pagina g
        LEFT JOIN parties pa
            ON pa.release_id = g.sample_release_id AND pa.party_id = g.entity_id
        LEFT JOIN party_master pm ON pm.party_id = g.entity_id
        ORDER BY g.r064_count DESC, g.entity_id;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *q.params)

        return {
            "data": [
                {
                    "entity": row["entity"],
                    "entity_id": row["entity_id"],
                    "total_processes": row["total_processes"],
                    "r064_count": row["r064_count"],
                    "r064_percentage": a_float(row["r064_percentage"]),
                }
                for row in rows
            ],
            "total_count": rows[0]["total_count"] if rows else 0,
            "group_by": AGRUPACION[rol],
        }

    async def get_r064_process_list(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        q = ConsultaSQL()
        procesos = self._procesos(q, year, buyer_id)
        query = f"""
        WITH {procesos}
        SELECT
            p.release_id,
            p.ocid,
            t.title,
            p.fecha AS process_date,
            p.contracts,
            p.amended_contracts,
            p.amendment_count,
            p.first_amendment_date,
            p.marcados_id,
            p.marcados_award,
            {nombre_comprador("p.release_id")} AS entity,
            COUNT(*) OVER () AS total_count
        FROM procesos p
        LEFT JOIN tender t ON t.release_id = p.release_id
        WHERE p.{MARCADO}
        ORDER BY p.first_amendment_date DESC NULLS LAST, p.release_id
        {q.paginar(limit, offset)};
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *q.params)

        return {
            "data": [
                {
                    "release_id": row["release_id"],
                    "ocid": row["ocid"],
                    "title": row["title"],
                    "process_date": row["process_date"],
                    "contracts": row["contracts"],
                    "amended_contracts": row["amended_contracts"],
                    "amendment_count": row["amendment_count"],
                    "first_amendment_date": row["first_amendment_date"],
                    "flagged_contracts": contratos_marcados(row),
                    "entity": row["entity"],
                }
                for row in rows
            ],
            "total_count": rows[0]["total_count"] if rows else 0,
        }
