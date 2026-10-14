from abc import ABC, abstractmethod
from typing import Dict, Any


class R064Repository(ABC):
    """
    Puerto para el acceso a datos del indicador R064.
    Contrato con modificaciones: proceso con al menos un contrato enmendado.
    Unidad de análisis: el proceso de contratación.
    """

    @abstractmethod
    async def get_r064_data(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Obtiene los datos agregados para R064.

        Retorna un diccionario con:
            - total_processes: int
            - r064_count: int
            - r064_percentage: float
        """
        ...

    @abstractmethod
    async def get_r064_time_series(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Obtiene la serie mensual con: month, total, r064_count, r064_percentage.
        """
        ...

    @abstractmethod
    async def get_r064_top_entities(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene las entidades con mayor cantidad de casos R064.
        Retorna un diccionario con:
            - data: list[dict] con entity, entity_id, total_processes, r064_count,
              r064_percentage
            - total_count: int (total de registros sin paginar)
            - group_by: 'buyer' sin buyer_id (una fila por entidad) o
              'procuring_entity' con buyer_id (unidades de esa entidad)
        """
        ...

    @abstractmethod
    async def get_r064_process_list(
        self,
        year: int | None = None,
        buyer_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene el listado de procesos que activan R064.
        Retorna un diccionario con:
            - data: list[dict] con release_id, ocid, title, process_date, contracts,
              amended_contracts, amendment_count, first_amendment_date,
              flagged_contracts, entity
            - total_count: int (total de registros sin paginar)
        """
        ...
