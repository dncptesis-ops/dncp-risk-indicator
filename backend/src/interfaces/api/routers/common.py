import logging

from fastapi import APIRouter, Depends
import asyncpg

from src.interfaces.api.dependencies import get_pool
from src.interfaces.api.schemas.common import (
    BuyersResponse,
    StatusResponse,
    YearsResponse,
)
from src.infrastructure.async_db.sql_common import (
    FECHA_CONTRATO,
    FECHA_LICITACION,
    fecha_inicio_indicadores,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/common", tags=["Common"])

# Cache en memoria, el worker la invalida despues de cada sync
# (POST /internal/invalidate-cache).
_cache: dict[str, dict] = {}


def invalidate_common_cache() -> None:
    """Limpia la caché de buyers/years. Llamar tras cada sync exitosa."""
    _cache.clear()
    logger.info("Caché de /common invalidada")


@router.get("/buyers", response_model=BuyersResponse)
async def get_buyers(pool: asyncpg.Pool = Depends(get_pool)):
    """Entidades compradoras (rol buyer), el mismo rol que usa el filtro buyer_id."""
    if "buyers" in _cache:
        return _cache["buyers"]

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                pr.party_id AS buyer_id,
                MAX(p.name) AS name
            FROM party_roles pr
            JOIN parties p
                ON p.release_id = pr.release_id
                AND p.party_id = pr.party_id
            WHERE pr.role = 'buyer'
            GROUP BY pr.party_id
            HAVING MAX(p.name) IS NOT NULL
            ORDER BY name;
            """)

    data = [{"buyer_id": r["buyer_id"], "name": r["name"]} for r in rows]
    result = {"data": data, "total_count": len(data)}
    _cache["buyers"] = result
    logger.info(f"Caché de buyers poblada ({len(data)} entidades)")
    return result


@router.get("/years", response_model=YearsResponse)
async def get_years(pool: asyncpg.Pool = Depends(get_pool)):
    """Años con datos en algún indicador, de mayor a menor.

    Usa las mismas fechas y el mismo rango que los indicadores.
    """
    if "years" in _cache:
        return _cache["years"]

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT DISTINCT EXTRACT(YEAR FROM fecha)::int AS year
            FROM (
                SELECT {FECHA_LICITACION} AS fecha
                FROM latest_releases r
                JOIN tender t ON t.release_id = r.release_id
                UNION ALL
                SELECT {FECHA_CONTRATO} AS fecha
                FROM latest_releases r
                JOIN contracts c ON c.release_id = r.release_id
            ) casos
            WHERE fecha >= $1 AND fecha <= NOW()
            ORDER BY year DESC;
            """,
            fecha_inicio_indicadores(),
        )

    result = {"years": [r["year"] for r in rows]}
    _cache["years"] = result
    logger.info(f"Caché de years poblada ({result['years']})")
    return result


@router.get("/status", response_model=StatusResponse)
async def get_status(pool: asyncpg.Pool = Depends(get_pool)):
    """Fecha de la última ejecución del worker. Si nunca se ejecutó, la del release más reciente."""
    async with pool.acquire() as conn:
        updated_at = await conn.fetchval("""
            SELECT COALESCE(
                (SELECT MAX(finished_at) FROM sync_log
                 WHERE status IN ('success', 'failed')),
                (SELECT MAX(date) FROM releases WHERE date <= NOW())
            );
            """)
    return {"updated_at": updated_at}
