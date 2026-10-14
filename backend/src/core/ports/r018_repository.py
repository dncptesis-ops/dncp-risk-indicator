from abc import ABC, abstractmethod
from typing import Dict, Any


class R018Repository(ABC):
    """
    Puerto para el acceso a datos del indicador R018.
    Las implementaciones concretas (ej. asyncpg) proporcionan la consulta SQL.
    """

    @abstractmethod
    async def get_r018_data(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Obtiene los datos agregados para R018.

        Retorna un diccionario con:
            - total_competitive: int
            - r018_count: int
            - r018_percentage: float
        """
        ...

    @abstractmethod
    async def get_r018_time_series(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Obtiene la serie mensual con: month, total, r018_count, r018_percentage.
        Devuelve una lista de diccionarios.
        """
        ...

    @abstractmethod
    async def get_r018_top_entities(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene las entidades con mayor cantidad de casos R018.
        Retorna un diccionario con:
            - data: list[dict] con entity, entity_id, total_competitive, r018_count, r018_percentage
            - total_count: int (total de registros sin paginar)
            - group_by: 'buyer' sin buyer_id (una fila por entidad) o
              'procuring_entity' con buyer_id (unidades de esa entidad)
        """
        ...

    @abstractmethod
    async def get_r018_top_suppliers(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene los proveedores que más veces han sido el único oferente
        en procesos competitivos (R018).

        Retorna un diccionario con:
            - data: list[dict] con tenderer_id, supplier_name, ruc, sole_bidder_count
            - total_count: int (total de registros sin paginar)
        """
        ...


    @abstractmethod
    async def get_r018_tender_list(
        self,
        year: int | None = None,
        proc_method: str | None = None,
        buyer_id: str | None = None,
        supplier_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene el listado de licitaciones que activan la bandera R018
        (único oferente en procedimiento competitivo).

        Retorna un diccionario con:
            - data: list[dict] con release_id, title, ocid, procurement_method,
              procedure_date, unique_tenderers, suppliers
            - total_count: int (total de registros sin paginar)
        """
        ...


