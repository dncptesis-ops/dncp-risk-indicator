from abc import ABC, abstractmethod
from typing import Dict, Any


class R063Repository(ABC):
    """
    Puerto para el acceso a datos del indicador R063.
    Contrato no publicado: proceso con un contrato activo sin documento firmado.
    Unidad de análisis: el proceso de contratación.
    """

    @abstractmethod
    async def get_r063_data(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Obtiene los datos agregados para R063.

        Retorna un diccionario con:
            - total_processes: int
            - r063_count: int
            - r063_percentage: float
        """
        ...

    @abstractmethod
    async def get_r063_time_series(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Obtiene la serie mensual con: month, total, r063_count, r063_percentage.
        """
        ...

    @abstractmethod
    async def get_r063_top_entities(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene las entidades con mayor cantidad de casos R063.
        Retorna un diccionario con:
            - data: list[dict] con entity, entity_id, total_processes, r063_count,
              r063_percentage
            - total_count: int (total de registros sin paginar)
            - group_by: 'buyer' sin buyer_id (una fila por entidad) o
              'procuring_entity' con buyer_id (unidades de esa entidad)
        """
        ...

    @abstractmethod
    async def get_r063_process_list(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene el listado de procesos que activan R063.
        Retorna un diccionario con:
            - data: list[dict] con release_id, ocid, title, process_date, active_contracts,
              unsigned_contracts, flagged_contracts, entity
            - total_count: int (total de registros sin paginar)
        """
        ...
