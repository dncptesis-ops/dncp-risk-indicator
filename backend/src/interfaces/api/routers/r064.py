from fastapi import APIRouter, Depends, Query
from src.interfaces.api.dependencies import get_r064_service, year_filter
from src.core.services.r064_service import R064Service
from src.interfaces.api.schemas.r064 import (
    R064KpiResponse,
    R064TimeSeriesResponse,
    R064TopEntitiesResponse,
    R064ProcessListResponse,
)

router = APIRouter(prefix="/r064", tags=["R064 Indicator"])


@router.get("/kpi", response_model=R064KpiResponse)
async def get_r064_kpi(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    service: R064Service = Depends(get_r064_service),
):
    """
    Indicador R064 (contrato con modificaciones): porcentaje de procesos con al
    menos un contrato activo o terminado que tiene enmiendas.
    """
    return await service.calculate(year, buyer_id)


@router.get("/monthly", response_model=R064TimeSeriesResponse)
async def get_r064_monthly(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    service: R064Service = Depends(get_r064_service),
):
    """
    Serie mensual del indicador R064. Cada proceso cuenta en el mes de su primer
    contrato (fecha de firma o, si falta, de inicio), no en el de sus enmiendas.
    """
    return await service.get_time_series(year, buyer_id)


@router.get("/top-entities", response_model=R064TopEntitiesResponse)
async def get_r064_top_entities(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    limit: int = Query(
        10, ge=1, le=10000, description="Cantidad de entidades a mostrar"
    ),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: R064Service = Depends(get_r064_service),
):
    """
    Ranking de entidades con más procesos R064 (contratos modificados).
    """
    return await service.get_top_entities(year, buyer_id, limit, offset)


@router.get("/processes", response_model=R064ProcessListResponse)
async def get_r064_processes(
    year: int | None = Depends(year_filter),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    limit: int = Query(100, ge=1, le=10000, description="Cantidad máxima de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: R064Service = Depends(get_r064_service),
):
    """
    Listado de procesos que activaron R064 (algún contrato con enmiendas),
    del más reciente al más antiguo según la primera enmienda.
    """
    return await service.get_process_list(
        year=year,
        buyer_id=buyer_id,
        limit=limit,
        offset=offset,
    )
