from fastapi import APIRouter, Depends, Query
from src.interfaces.api.dependencies import get_r018_service, year_filter, MetodoCompetitivo
from src.core.services.r018_service import R018Service
from src.interfaces.api.schemas.r018 import (
    R018KpiResponse,
    R018TimeSeriesResponse,
    R018TopEntitiesResponse,
    R018TopSuppliersResponse,
    R018TenderListResponse,
)

router = APIRouter(prefix="/r018", tags=["R018 Indicator"])


@router.get("/kpi", response_model=R018KpiResponse)
async def get_r018_kpi(
    year: int | None = Depends(year_filter),
    proc_method: MetodoCompetitivo | None = Query(
        None, description="Método de contratación (open, selective)"
    ),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    service: R018Service = Depends(get_r018_service),
):
    """
    Calcula el indicador R018: porcentaje de licitaciones competitivas
    con un único oferente.
    """
    return await service.calculate(year, proc_method, buyer_id)


@router.get("/monthly", response_model=R018TimeSeriesResponse)
async def get_r018_monthly(
    year: int | None = Depends(year_filter),
    proc_method: MetodoCompetitivo | None = Query(
        None, description="Método de contratación (open, selective)"
    ),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    service: R018Service = Depends(get_r018_service),
):
    """
    Calcula el indicador R018: porcentaje de licitaciones competitivas
    con un único oferente.
    """
    return await service.get_time_series(year, proc_method, buyer_id)


@router.get("/top-entities", response_model=R018TopEntitiesResponse)
async def get_r018_top_entities(
    year: int | None = Depends(year_filter),
    proc_method: MetodoCompetitivo | None = Query(
        None, description="Método de contratación (open, selective)"
    ),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    limit: int = Query(10, ge=1, le=10000, description="Cantidad de entidades a mostrar"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: R018Service = Depends(get_r018_service),
):
    """
    Ranking de entidades con mayor concentración de casos R018 (licitaciones de único oferente).
    """
    return await service.get_top_entities(year, proc_method, buyer_id, limit, offset)


@router.get("/suppliers", response_model=R018TopSuppliersResponse)
async def get_top_suppliers(
    year: int | None = Depends(year_filter),
    proc_method: MetodoCompetitivo | None = Query(
        None, description="Método de contratación (open, selective)"
    ),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    limit: int = Query(10, ge=1, le=10000, description="Cantidad máxima de proveedores"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: R018Service = Depends(get_r018_service),
):
    """
    Ranking de proveedores que más veces han sido el único oferente
    en procesos competitivos (indicador R018).
    """
    return await service.get_top_suppliers(year, proc_method, buyer_id, limit, offset)


@router.get("/tenders", response_model=R018TenderListResponse)
async def get_r018_tenders(
    year: int | None = Depends(year_filter),
    proc_method: MetodoCompetitivo | None = Query(
        None, description="Método de contratación (open, selective)"
    ),
    buyer_id: str | None = Query(
        None, description="Entidad compradora (buyer): su party_id"
    ),
    supplier_id: str | None = Query(None, description="ID del proveedor (tenderer_id)"),
    limit: int = Query(100, ge=1, le=10000, description="Cantidad máxima de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: R018Service = Depends(get_r018_service),
):
    """
    Devuelve el listado de licitaciones que activaron la bandera R018
    (único oferente en procedimiento competitivo).
    Se puede filtrar por comprador, proveedor, año y método.
    """
    return await service.get_tender_list(
        year=year,
        proc_method=proc_method,
        buyer_id=buyer_id,
        supplier_id=supplier_id,
        limit=limit,
        offset=offset,
    )
