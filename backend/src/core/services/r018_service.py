from src.core.ports.r018_repository import R018Repository
from src.interfaces.api.schemas.r018 import (
    R018KpiResponse,
    R018Filters,
    R018MonthlyItem,
    R018TimeSeriesResponse,
    R018TopEntitiesResponse,
    R018TopEntityItem,
    R018TopSupplierItem,
    R018TopSuppliersResponse,
    R018TenderListResponse,
    R018TenderItem,
)


class R018Service:
    """Caso de uso: cálculo del indicador de riesgo R018."""

    def __init__(self, repository: R018Repository):
        self._repo = repository

    async def calculate(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
    ) -> R018KpiResponse:
        """
        Obtiene KPI R018.
        Args:
            year: Año para filtrar (opcional).
            proc_method: Método de contratación (opcional).
            buyer_id: ID del comprador (opcional).
        Returns:
            R018KpiResponse con los indicadores y los filtros aplicados.
        """
        raw = await self._repo.get_r018_data(year, proc_method, buyer_id)
        return R018KpiResponse(
            total_competitive=raw["total_competitive"] or 0,
            r018_count=raw["r018_count"] or 0,
            r018_percentage=raw["r018_percentage"] or 0,
            applied_filters=R018Filters(
                year=year,
                procurement_method=proc_method,
                buyer_id=buyer_id,
            ),
        )

    async def get_time_series(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
    ) -> R018TimeSeriesResponse:
        """
        Obtiene las series temporales mensuales
        Args:
            year: Año para filtrar (opcional).
            proc_method: Método de contratación (opcional).
            buyer_id: ID del comprador (opcional).
        Returns:
            R018TimeSeriesResponse con los datos y filtros aplicados
        """
        raw = await self._repo.get_r018_time_series(year, proc_method, buyer_id)

        monthly_items = [R018MonthlyItem(**item) for item in raw]

        return R018TimeSeriesResponse(
            data=monthly_items,
            applied_filters=R018Filters(
                year=year,
                procurement_method=proc_method,
                buyer_id=buyer_id,
            ),
        )

    async def get_top_entities(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> R018TopEntitiesResponse:
        """
        Obtiene el top de entidades
        Returns
            R018TopEntitiesResponse con los datos, total_count y filtros
        """
        raw = await self._repo.get_r018_top_entities(
            year, proc_method, buyer_id, limit, offset
        )

        items = [R018TopEntityItem(**item) for item in raw["data"]]

        return R018TopEntitiesResponse(
            data=items,
            total_count=raw["total_count"],
            group_by=raw["group_by"],
            limit=limit,
            offset=offset,
            applied_filters=R018Filters(
                year=year,
                procurement_method=proc_method,
                buyer_id=buyer_id,
            ),
        )

    async def get_top_suppliers(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> R018TopSuppliersResponse:
        raw = await self._repo.get_r018_top_suppliers(
            year, proc_method, buyer_id, limit, offset
        )

        items = [R018TopSupplierItem(**item) for item in raw["data"]]

        return R018TopSuppliersResponse(
            data=items,
            total_count=raw["total_count"],
            limit=limit,
            offset=offset,
            applied_filters=R018Filters(
                year=year,
                procurement_method=proc_method,
                buyer_id=buyer_id,
            ),
        )

    async def get_tender_list(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        supplier_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> R018TenderListResponse:
        raw = await self._repo.get_r018_tender_list(
            year, proc_method, buyer_id, supplier_id, limit, offset
        )
        items = []
        for item in raw["data"]:
            ocid = item.get("ocid")
            url_api = None
            if ocid:
                url_api = f"https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/{ocid}"
            items.append(
                R018TenderItem(
                    release_id=item["release_id"],
                    ocid=ocid,
                    title=item["title"],
                    procurement_method=item["procurement_method"],
                    procedure_date=item["procedure_date"],
                    unique_tenderers=item["unique_tenderers"],
                    suppliers=item["suppliers"],
                    api_url=url_api,
                )
            )
        return R018TenderListResponse(
            data=items,
            total_count=raw["total_count"],
            limit=limit,
            offset=offset,
            applied_filters=R018Filters(
                year=year,
                procurement_method=proc_method,
                buyer_id=buyer_id,
                supplier_id=supplier_id,
            ),
        )
