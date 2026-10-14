from fastapi import APIRouter, Depends, Query
from src.interfaces.api.dependencies import get_r063_service, year_filter
from src.core.services.r063_service import R063Service
from src.interfaces.api.schemas.r063 import (
    R063KpiResponse,
    R063TimeSeriesResponse,
    R063TopEntitiesResponse,
    R063ProcessListResponse,
)

router = APIRouter(prefix="/r063", tags=["R063 Indicator"])


@router.get("/kpi", response_model=R063KpiResponse)
async def get_r063_kpi(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    service: R063Service = Depends(get_r063_service),
):
    """
    Indicador R063 (contrato no publicado): porcentaje de procesos con al menos
    un contrato activo cuyo documento firmado (contractSigned) no está publicado.
    """
    return await service.calculate(year, buyer_id)


@router.get("/monthly", response_model=R063TimeSeriesResponse)
async def get_r063_monthly(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    service: R063Service = Depends(get_r063_service),
):
    """
    Serie mensual del indicador R063. Cada proceso cuenta en el mes de su primer contrato activo.
    """
    return await service.get_time_series(year, buyer_id)


@router.get("/top-entities", response_model=R063TopEntitiesResponse)
async def get_r063_top_entities(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    limit: int = Query(
        10, ge=1, le=10000, description="Cantidad de entidades a mostrar"
    ),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: R063Service = Depends(get_r063_service),
):
    """
    Ranking de entidades con más procesos R063 (contrato activo sin documento firmado).
    """
    return await service.get_top_entities(year, buyer_id, limit, offset)


@router.get("/processes", response_model=R063ProcessListResponse)
async def get_r063_processes(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    limit: int = Query(100, ge=1, le=10000, description="Cantidad máxima de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: R063Service = Depends(get_r063_service),
):
    """
    Listado de procesos que activaron R063 (algún contrato activo sin documento
    firmado publicado). Se puede filtrar por comprador y año.
    """
    return await service.get_process_list(
        year=year,
        buyer_id=buyer_id,
        limit=limit,
        offset=offset,
    )
