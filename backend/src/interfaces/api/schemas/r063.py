from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.schemas.common import FlaggedContract


class R063Filters(BaseModel):
    """Filtros aplicados en la consulta (solo los que el usuario envió)."""

    year: int | None = Field(
        None, description="Año del proceso (fecha de su primer contrato activo)"
    )
    buyer_id: str | None = Field(None, alias="buyerId", description="ID del comprador")

    model_config = ConfigDict(populate_by_name=True)


class R063KpiResponse(BaseModel):
    """Respuesta agregada del indicador R063 (sin desglose mensual)."""

    total_processes: int = Field(
        ..., description="Procesos con al menos un contrato activo"
    )
    r063_count: int = Field(
        ...,
        description="Procesos con algún contrato activo sin documento firmado publicado (R063)",
    )
    r063_percentage: float = Field(..., description="Porcentaje de procesos R063")
    applied_filters: R063Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R063MonthlyItem(BaseModel):
    """Indicador R063 agregado por mes (según la fecha del primer contrato activo)."""

    month: str = Field(..., description="Mes en formato YYYY-MM")
    total: int = Field(..., description="Procesos con contrato activo en el mes")
    r063_count: int = Field(..., description="Procesos R063 en el mes")
    r063_percentage: float = Field(
        ..., description="Porcentaje de procesos R063 en el mes"
    )


class R063TimeSeriesResponse(BaseModel):
    """Respuesta con desglose mensual del indicador R063."""

    data: list[R063MonthlyItem] = Field(
        ..., description="Lista de indicadores agregados por mes"
    )
    applied_filters: R063Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R063TopEntityItem(BaseModel):
    """Entidad en top de R063."""

    entity: str = Field(
        ..., description="Nombre de la entidad o unidad de contratación"
    )
    entity_id: str = Field(
        ...,
        description="party_id de la entidad (buyer) o, con buyer_id, de la unidad (procuringEntity)",
    )
    total_processes: int = Field(
        ...,
        description="Procesos de la entidad con al menos un contrato activo",
    )
    r063_count: int = Field(..., description="Procesos R063 de la entidad")
    r063_percentage: float = Field(
        ..., description="Porcentaje de procesos R063 en la entidad"
    )


class R063TopEntitiesResponse(BaseModel):
    """Respuesta con top entidades con más procesos R063."""

    data: list[R063TopEntityItem] = Field(
        ...,
        description="Lista top de entidades ordenada por cantidad de procesos R063 descendente",
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
    applied_filters: R063Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R063ProcessItem(BaseModel):
    """Detalle de un proceso que activó R063."""

    release_id: str = Field(..., description="ID del release vigente del proceso")
    ocid: str | None = Field(None, description="OCID del proceso")
    title: str | None = Field(None, description="Título de la licitación")
    process_date: datetime = Field(
        ..., description="Fecha del primer contrato activo (firma o inicio), ISO 8601"
    )
    active_contracts: int = Field(..., description="Contratos activos del proceso")
    unsigned_contracts: int = Field(
        ..., description="Contratos activos sin documento firmado publicado"
    )
    flagged_contracts: list[FlaggedContract] = Field(
        ...,
        description="Contratos activos sin documento firmado publicado: código y award_id de cada uno",
    )
    entity: str | None = Field(None, description="Nombre de la entidad compradora")
    api_url: str | None = Field(None, description="Enlace a la API con datos completos")


class R063ProcessListResponse(BaseModel):
    """Listado de procesos R063."""

    data: list[R063ProcessItem] = Field(..., description="Lista de procesos")
    total_count: int = Field(..., description="Total de registros sin paginar")
    limit: int = Field(..., description="Límite aplicado en la consulta")
    offset: int = Field(..., description="Offset aplicado en la consulta")
    applied_filters: R063Filters = Field(..., description="Filtros utilizados")
