from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.schemas.common import FlaggedContract


class R064Filters(BaseModel):
    """Filtros aplicados en la consulta (solo los que el usuario envió)."""

    year: int | None = Field(
        None, description="Año del proceso (fecha de su primer contrato)"
    )
    buyer_id: str | None = Field(None, alias="buyerId", description="ID del comprador")

    model_config = ConfigDict(populate_by_name=True)


class R064KpiResponse(BaseModel):
    """Respuesta agregada del indicador R064 (sin desglose mensual)."""

    total_processes: int = Field(
        ..., description="Procesos con al menos un contrato activo o terminado"
    )
    r064_count: int = Field(
        ..., description="Procesos con al menos un contrato enmendado (R064)"
    )
    r064_percentage: float = Field(..., description="Porcentaje de procesos R064")
    applied_filters: R064Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R064MonthlyItem(BaseModel):
    """Indicador R064 agregado por mes (según la fecha del primer contrato)."""

    month: str = Field(..., description="Mes en formato YYYY-MM")
    total: int = Field(..., description="Procesos cuyo primer contrato es de ese mes")
    r064_count: int = Field(
        ..., description="De esos procesos, los que tienen algún contrato enmendado"
    )
    r064_percentage: float = Field(
        ..., description="Porcentaje de procesos R064 en el mes"
    )


class R064TimeSeriesResponse(BaseModel):
    """Respuesta con desglose mensual del indicador R064."""

    data: list[R064MonthlyItem] = Field(
        ..., description="Lista de indicadores agregados por mes"
    )
    applied_filters: R064Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R064TopEntityItem(BaseModel):
    """Entidad en top de R064."""

    entity: str = Field(..., description="Nombre de la entidad o unidad de contratación")
    entity_id: str = Field(
        ...,
        description="party_id de la entidad (buyer) o, con buyer_id, de la unidad (procuringEntity)",
    )
    total_processes: int = Field(
        ...,
        description="Procesos de la entidad con al menos un contrato activo o terminado",
    )
    r064_count: int = Field(..., description="Procesos R064 de la entidad")
    r064_percentage: float = Field(
        ..., description="Porcentaje de procesos R064 en la entidad"
    )


class R064TopEntitiesResponse(BaseModel):
    """Respuesta con top entidades con más procesos R064."""

    data: list[R064TopEntityItem] = Field(
        ...,
        description="Lista top de entidades ordenada por cantidad de procesos R064 descendente",
    )
    total_count: int = Field(..., description="Total de registros sin paginar")
    group_by: Literal["buyer", "procuring_entity"] = Field(
        ...,
        description=(
            "Criterio del ranking: 'buyer' (entidad que paga) sin filtro; "
            "'procuring_entity' (unidades de contratación de la entidad) con buyer_id"
        ),
    )
    limit: int = Field(..., description="Límite aplicado en la consulta")
    offset: int = Field(..., description="Offset aplicado en la consulta")
    applied_filters: R064Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R064ProcessItem(BaseModel):
    """Detalle de un proceso que activó R064."""

    release_id: str = Field(..., description="ID del release vigente del proceso")
    ocid: str | None = Field(None, description="OCID del proceso")
    title: str | None = Field(None, description="Título de la licitación")
    process_date: datetime = Field(
        ..., description="Fecha del primer contrato (firma o inicio), ISO 8601"
    )
    contracts: int = Field(
        ..., description="Contratos activos o terminados del proceso"
    )
    amended_contracts: int = Field(
        ..., description="Contratos con al menos una enmienda"
    )
    amendment_count: int = Field(..., description="Total de enmiendas del proceso")
    first_amendment_date: datetime | None = Field(
        None, description="Fecha de la primera enmienda (ISO 8601), si está publicada"
    )
    flagged_contracts: list[FlaggedContract] = Field(
        ..., description="Contratos con al menos una enmienda: código y award_id de cada uno"
    )
    entity: str | None = Field(None, description="Nombre de la entidad compradora")
    api_url: str | None = Field(None, description="Enlace a la API con datos completos")


class R064ProcessListResponse(BaseModel):
    """Listado de procesos R064."""

    data: list[R064ProcessItem] = Field(..., description="Lista de procesos")
    total_count: int = Field(..., description="Total de registros sin paginar")
    limit: int = Field(..., description="Límite aplicado en la consulta")
    offset: int = Field(..., description="Offset aplicado en la consulta")
    applied_filters: R064Filters = Field(..., description="Filtros utilizados")
