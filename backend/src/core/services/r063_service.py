from src.core.ports.r063_repository import R063Repository
from src.interfaces.api.schemas.r063 import (
    R063KpiResponse,
    R063Filters,
    R063MonthlyItem,
    R063TimeSeriesResponse,
    R063TopEntitiesResponse,
    R063TopEntityItem,
    R063ProcessListResponse,
    R063ProcessItem,
)


class R063Service:
    """Caso de uso: cálculo del indicador de riesgo R063."""

    def __init__(self, repository: R063Repository):
        self._repo = repository

    async def calculate(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> R063KpiResponse:
        """
        Obtiene KPI R063.
        Args:
            year: Año para filtrar (opcional).
            buyer_id: ID del comprador (opcional).
        Returns:
            R063KpiResponse con los indicadores y los filtros aplicados.
        """
        raw = await self._repo.get_r063_data(year, buyer_id)
        return R063KpiResponse(
            total_processes=raw["total_processes"] or 0,
            r063_count=raw["r063_count"] or 0,
            r063_percentage=raw["r063_percentage"] or 0,
            applied_filters=R063Filters(
                year=year,
                buyer_id=buyer_id,
            ),
        )

    async def get_time_series(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> R063TimeSeriesResponse:
        """
        Obtiene las series temporales mensuales
        Args:
            year: Año para filtrar (opcional).
            buyer_id: ID del comprador (opcional).
        Returns:
            R063TimeSeriesResponse con los datos y filtros aplicados
        """
        raw = await self._repo.get_r063_time_series(year, buyer_id)

        monthly_items = [R063MonthlyItem(**item) for item in raw]

        return R063TimeSeriesResponse(
            data=monthly_items,
            applied_filters=R063Filters(
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
    ) -> R063TopEntitiesResponse:
        """
        Obtiene el top de entidades
        Returns
            R063TopEntitiesResponse con los datos y filtros
        """
        raw = await self._repo.get_r063_top_entities(year, buyer_id, limit, offset)

        items = [R063TopEntityItem(**item) for item in raw["data"]]

        return R063TopEntitiesResponse(
            data=items,
            total_count=raw["total_count"],
            group_by=raw["group_by"],
            limit=limit,
            offset=offset,
            applied_filters=R063Filters(
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
    ) -> R063ProcessListResponse:
        """
        Obtiene el listado paginado de procesos que activan R063.
        """
        raw = await self._repo.get_r063_process_list(year, buyer_id, limit, offset)
        items = []
        for item in raw["data"]:
            ocid = item.get("ocid")
            url_api = None
            if ocid:
                url_api = f"https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/{ocid}"
            items.append(
                R063ProcessItem(
                    release_id=item["release_id"],
                    ocid=ocid,
                    title=item["title"],
                    process_date=item["process_date"],
                    active_contracts=item["active_contracts"],
                    unsigned_contracts=item["unsigned_contracts"],
                    flagged_contracts=item["flagged_contracts"],
                    entity=item["entity"],
                    api_url=url_api,
                )
            )
        return R063ProcessListResponse(
            data=items,
            total_count=raw["total_count"],
            limit=limit,
            offset=offset,
            applied_filters=R063Filters(
                year=year,
                buyer_id=buyer_id,
            ),
        )
