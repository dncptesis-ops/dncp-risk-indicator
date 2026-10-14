from src.core.ports.r064_repository import R064Repository
from src.interfaces.api.schemas.r064 import (
    R064KpiResponse,
    R064Filters,
    R064MonthlyItem,
    R064TimeSeriesResponse,
    R064TopEntitiesResponse,
    R064TopEntityItem,
    R064ProcessListResponse,
    R064ProcessItem,
)


class R064Service:
    """Caso de uso: cálculo del indicador de riesgo R064."""

    def __init__(self, repository: R064Repository):
        self._repo = repository

    async def calculate(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> R064KpiResponse:
        """
        Obtiene KPI R064.
        Args:
            year: Año para filtrar (opcional).
            buyer_id: ID del comprador (opcional).
        Returns:
            R064KpiResponse con los indicadores y los filtros aplicados.
        """
        raw = await self._repo.get_r064_data(year, buyer_id)
        return R064KpiResponse(
            total_processes=raw["total_processes"] or 0,
            r064_count=raw["r064_count"] or 0,
            r064_percentage=raw["r064_percentage"] or 0,
            applied_filters=R064Filters(
                year=year,
                buyer_id=buyer_id,
            ),
        )

    async def get_time_series(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> R064TimeSeriesResponse:
        """
        Obtiene las series temporales mensuales.
        """
        raw = await self._repo.get_r064_time_series(year, buyer_id)

        monthly_items = [R064MonthlyItem(**item) for item in raw]

        return R064TimeSeriesResponse(
            data=monthly_items,
            applied_filters=R064Filters(
                year=year,
                buyer_id=buyer_id,
            ),
        )

    async def get_top_entities(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> R064TopEntitiesResponse:
        """
        Obtiene el top de entidades con más procesos con contratos modificados.
        """
        raw = await self._repo.get_r064_top_entities(year, buyer_id, limit, offset)

        items = [R064TopEntityItem(**item) for item in raw["data"]]

        return R064TopEntitiesResponse(
            data=items,
            total_count=raw["total_count"],
            group_by=raw["group_by"],
            limit=limit,
            offset=offset,
            applied_filters=R064Filters(
                year=year,
                buyer_id=buyer_id,
            ),
        )

    async def get_process_list(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> R064ProcessListResponse:
        """
        Obtiene el listado paginado de procesos que activan R064.
        """
        raw = await self._repo.get_r064_process_list(year, buyer_id, limit, offset)
        items = []
        for item in raw["data"]:
            ocid = item.get("ocid")
            url_api = None
            if ocid:
                url_api = f"https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/{ocid}"
            items.append(
                R064ProcessItem(
                    release_id=item["release_id"],
                    ocid=ocid,
                    title=item["title"],
                    process_date=item["process_date"],
                    contracts=item["contracts"],
                    amended_contracts=item["amended_contracts"],
                    amendment_count=item["amendment_count"],
                    first_amendment_date=item["first_amendment_date"],
                    flagged_contracts=item["flagged_contracts"],
                    entity=item["entity"],
                    api_url=url_api,
                )
            )
        return R064ProcessListResponse(
            data=items,
            total_count=raw["total_count"],
            limit=limit,
            offset=offset,
            applied_filters=R064Filters(
                year=year,
                buyer_id=buyer_id,
            ),
        )
