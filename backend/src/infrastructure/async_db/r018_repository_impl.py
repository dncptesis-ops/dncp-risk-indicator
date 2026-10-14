import asyncpg
from typing import Dict, Any
from src.core.ports.r018_repository import R018Repository
from src.infrastructure.async_db.sql_common import (
    FECHA_LICITACION,
    AGRUPACION,
    SIN_NOMBRE_ENTIDAD,
    SIN_NOMBRE_PROVEEDOR,
    ConsultaSQL,
    a_float,
    porcentaje,
    rol_ranking,
)

# un solo oferente declarado
UNICO = "number_of_tenderers = 1"


class AsyncpgR018Repository(R018Repository):
    """R018: licitaciones competitivas (open o selective) con un único oferente.

    Se cuenta por proceso y la fecha es el fin del período de ofertas.
    """

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    @staticmethod
    def _procesos(
        q: ConsultaSQL,
        year: int | None,
        proc_method: str | None,
        buyer_id: str | None,
        supplier_id: str | None = None,
        solo_unico: bool = False,
    ) -> str:
        """CTE procesos: una fila por licitación competitiva."""
        condiciones = [
            "t.procurement_method IN ('open', 'selective')",
            "t.number_of_tenderers IS NOT NULL",
            q.rango_valido(FECHA_LICITACION),
            q.anio(FECHA_LICITACION, year),
            q.comprador("r.release_id", buyer_id),
        ]
        if proc_method is not None:
            condiciones.append(f"t.procurement_method = {q.param(proc_method)}")
        if supplier_id is not None:
            condiciones.append(f"""r.release_id IN (
                SELECT tr.release_id FROM tenderers tr
                WHERE tr.tenderer_id = {q.param(supplier_id)}
            )""")
        if solo_unico:
            condiciones.append(f"t.{UNICO}")
        return f"""procesos AS MATERIALIZED (
            SELECT
                r.release_id,
                r.ocid,
                t.title,
                t.procurement_method,
                t.number_of_tenderers,
                {FECHA_LICITACION} AS fecha
            FROM latest_releases r
            JOIN tender t ON t.release_id = r.release_id
            WHERE {" AND ".join(condiciones)}
        )"""

    async def get_r018_data(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
    ) -> Dict[str, Any]:
        q = ConsultaSQL()
        query = f"""
        WITH {self._procesos(q, year, proc_method, buyer_id)}
        SELECT
            COUNT(*) AS total_competitive,
            COUNT(*) FILTER (WHERE {UNICO}) AS r018_count,
            {porcentaje(f"COUNT(*) FILTER (WHERE {UNICO})", "COUNT(*)")} AS r018_percentage
        FROM procesos;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *q.params)

        return {
            "total_competitive": row["total_competitive"],
            "r018_count": row["r018_count"],
            "r018_percentage": a_float(row["r018_percentage"]),
        }

    async def get_r018_time_series(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        q = ConsultaSQL()
        query = f"""
        WITH {self._procesos(q, year, proc_method, buyer_id)}
        SELECT
            TO_CHAR(DATE_TRUNC('month', fecha), 'YYYY-MM') AS month,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE {UNICO}) AS r018_count,
            {porcentaje(f"COUNT(*) FILTER (WHERE {UNICO})", "COUNT(*)")} AS r018_percentage
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
                "r018_count": row["r018_count"],
                "r018_percentage": a_float(row["r018_percentage"]),
            }
            for row in rows
        ]

    async def get_r018_top_entities(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        q = ConsultaSQL()
        procesos = self._procesos(q, year, proc_method, buyer_id)
        # sin filtro agrupa por buyer; con buyer_id, por sus unidades
        rol = rol_ranking(buyer_id)
        query = f"""
        WITH {procesos},
        por_entidad AS (
            SELECT
                pr.party_id AS entity_id,
                MAX(p.release_id) AS sample_release_id,
                COUNT(DISTINCT p.release_id) AS total_competitive,
                COUNT(DISTINCT p.release_id) FILTER (WHERE p.{UNICO}) AS r018_count
            FROM procesos p
            JOIN party_roles pr
                ON pr.release_id = p.release_id
                AND pr.role = '{rol}'
            GROUP BY pr.party_id
            HAVING COUNT(DISTINCT p.release_id) FILTER (WHERE p.{UNICO}) > 0
        ),
        pagina AS (
            SELECT *, COUNT(*) OVER () AS total_count
            FROM por_entidad
            ORDER BY r018_count DESC, entity_id
            {q.paginar(limit, offset)}
        )
        SELECT
            COALESCE(pa.name, pm.name, '{SIN_NOMBRE_ENTIDAD}') AS entity,
            g.entity_id,
            g.total_competitive,
            g.r018_count,
            {porcentaje("g.r018_count", "g.total_competitive")} AS r018_percentage,
            g.total_count
        FROM pagina g
        LEFT JOIN parties pa
            ON pa.release_id = g.sample_release_id AND pa.party_id = g.entity_id
        LEFT JOIN party_master pm ON pm.party_id = g.entity_id
        ORDER BY g.r018_count DESC, g.entity_id;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *q.params)

        return {
            "data": [
                {
                    "entity": row["entity"],
                    "entity_id": row["entity_id"],
                    "total_competitive": row["total_competitive"],
                    "r018_count": row["r018_count"],
                    "r018_percentage": a_float(row["r018_percentage"]),
                }
                for row in rows
            ],
            "total_count": rows[0]["total_count"] if rows else 0,
            "group_by": AGRUPACION[rol],
        }

    async def get_r018_top_suppliers(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        q = ConsultaSQL()
        procesos = self._procesos(q, year, proc_method, buyer_id, solo_unico=True)
        query = f"""
        WITH {procesos},
        proveedor_unico AS (
            -- un proveedor por proceso, el que tiene nombre
            SELECT DISTINCT ON (p.release_id)
                p.release_id,
                tr.tenderer_id
            FROM procesos p
            JOIN tenderers tr ON tr.release_id = p.release_id
            ORDER BY
                p.release_id,
                tr.tenderer_id IN (SELECT party_id FROM party_master) DESC,
                LENGTH(tr.tenderer_id) DESC,
                tr.tenderer_id
        ),
        por_proveedor AS (
            SELECT
                tenderer_id,
                MAX(release_id) AS sample_release_id,
                COUNT(*) AS sole_bidder_count
            FROM proveedor_unico
            GROUP BY tenderer_id
        ),
        pagina AS (
            SELECT *, COUNT(*) OVER () AS total_count
            FROM por_proveedor
            ORDER BY sole_bidder_count DESC, tenderer_id
            {q.paginar(limit, offset)}
        )
        SELECT
            g.tenderer_id,
            COALESCE(tr.name, pa.name, pm.name, '{SIN_NOMBRE_PROVEEDOR}') AS supplier_name,
            -- el id viene como PY-RUC-80013889-9, se muestra solo el número
            COALESCE(
                CASE WHEN pa.identifier_scheme = 'PY-RUC' THEN pa.identifier_id END,
                CASE WHEN g.tenderer_id ~ '^PY-RUC-[0-9]'
                     THEN substring(g.tenderer_id FROM 8) END,
                'Sin RUC'
            ) AS ruc,
            g.sole_bidder_count,
            g.total_count
        FROM pagina g
        LEFT JOIN tenderers tr
            ON tr.release_id = g.sample_release_id AND tr.tenderer_id = g.tenderer_id
        LEFT JOIN parties pa
            ON pa.release_id = g.sample_release_id AND pa.party_id = g.tenderer_id
        LEFT JOIN party_master pm ON pm.party_id = g.tenderer_id
        ORDER BY g.sole_bidder_count DESC, g.tenderer_id;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *q.params)

        return {
            "data": [
                {
                    "tenderer_id": row["tenderer_id"],
                    "supplier_name": row["supplier_name"],
                    "ruc": row["ruc"],
                    "sole_bidder_count": row["sole_bidder_count"],
                }
                for row in rows
            ],
            "total_count": rows[0]["total_count"] if rows else 0,
        }

    async def get_r018_tender_list(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        supplier_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        q = ConsultaSQL()
        procesos = self._procesos(
            q, year, proc_method, buyer_id, supplier_id, solo_unico=True
        )
        query = f"""
        WITH {procesos}
        SELECT
            p.release_id,
            p.ocid,
            p.title,
            p.procurement_method,
            p.fecha AS procedure_date,
            p.number_of_tenderers AS unique_tenderers,
            COALESCE(
                (SELECT string_agg(
                            DISTINCT COALESCE(tr.name, pa.name, pm.name, '{SIN_NOMBRE_PROVEEDOR}'),
                            ', ')
                 FROM tenderers tr
                 LEFT JOIN parties pa
                     ON pa.release_id = tr.release_id AND pa.party_id = tr.tenderer_id
                 LEFT JOIN party_master pm ON pm.party_id = tr.tenderer_id
                 WHERE tr.release_id = p.release_id),
                '{SIN_NOMBRE_PROVEEDOR}'
            ) AS suppliers,
            COUNT(*) OVER () AS total_count
        FROM procesos p
        ORDER BY p.fecha DESC, p.release_id
        {q.paginar(limit, offset)};
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *q.params)

        return {
            "data": [
                {
                    "release_id": row["release_id"],
                    "title": row["title"],
                    "ocid": row["ocid"],
                    "procurement_method": row["procurement_method"],
                    "procedure_date": row["procedure_date"],
                    "unique_tenderers": row["unique_tenderers"],
                    "suppliers": row["suppliers"],
                }
                for row in rows
            ],
            "total_count": rows[0]["total_count"] if rows else 0,
        }
