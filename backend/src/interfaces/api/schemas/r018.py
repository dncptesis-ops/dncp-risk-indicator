from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class R018Filters(BaseModel):
    """Filtros aplicados en la consulta (solo los que el usuario envió)."""

    year: int | None = Field(None, description="Año de la licitación")
    procurement_method: str | None = Field(
        None, alias="procurementMethod", description="Método de contratación"
    )
    buyer_id: str | None = Field(None, alias="buyerId", description="ID del comprador")
    supplier_id: str | None = Field(
        None, alias="supplierId", description="ID del proveedor"
    )

    # permitimos filtros como camelCase además de snake_case
    model_config = ConfigDict(populate_by_name=True)


class R018KpiResponse(BaseModel):
    """Respuesta agregada del indicador R018 (sin desglose mensual)."""

    total_competitive: int = Field(
        ..., description="Total de licitaciones competitivas (open, selective)"
    )
    r018_count: int = Field(..., description="Casos con único oferente (R018)")
    r018_percentage: float = Field(..., description="Porcentaje de casos R018")
    applied_filters: R018Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R018MonthlyItem(BaseModel):
    """Indicador R018 agregado por mes."""

    month: str = Field(..., description="Mes en formato YYYY-MM")
    total: int = Field(..., description="Total de licitaciones competitivas en el mes")
    r018_count: int = Field(
        ..., description="Casos con único oferente (R018) en el mes"
    )
    r018_percentage: float = Field(
        ..., description="Porcentaje de casos R018 en el mes"
    )


class R018TimeSeriesResponse(BaseModel):
    """Respuesta con desglose mensual del indicador R018."""

    data: list[R018MonthlyItem] = Field(
        ..., description="Lista de indicadores agregados por mes"
    )
    applied_filters: R018Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R018TopEntityItem(BaseModel):
    """Entidad en top de R018."""

    entity: str = Field(..., description="Nombre de la entidad o unidad de contratación")
    entity_id: str = Field(
        ...,
        description="party_id de la entidad (buyer) o, con buyer_id, de la unidad (procuringEntity)",
    )
    total_competitive: int = Field(
        ...,
        description="Total de licitaciones competitivas (open, selective) de la entidad",
    )
    r018_count: int = Field(..., description="Cantidad de casos R018 de la entidad")
    r018_percentage: float = Field(..., description="Porcentaje de R018 en la entidad")


class R018TopEntitiesResponse(BaseModel):
    """Respuesta con top entidades con mayor porcentaje de R018."""

    data: list[R018TopEntityItem] = Field(
        ...,
        description="Lista top de entidades ordenado por cantidad de casos de R018 descendente",
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
    applied_filters: R018Filters = Field(
        ..., description="Filtros utilizados en la consulta"
    )


class R018TopSupplierItem(BaseModel):
    """Proveedor en el ranking de concentración."""

    tenderer_id: str = Field(..., description="ID del proveedor (party_id)")
    supplier_name: str = Field(..., description="Nombre del proveedor")
    ruc: str | None = Field(
        None, description="RUC del proveedor (ej. 80013889-9) o 'Sin RUC'"
    )
    sole_bidder_count: int = Field(
        ...,
        description="Cantidad de veces que fue único oferente en procesos competitivos",
    )


class R018TopSuppliersResponse(BaseModel):
    """Respuesta del ranking de proveedores con mayor recurrencia como único oferente."""

    data: list[R018TopSupplierItem] = Field(
        ..., description="Proveedores ordenados por recurrencia descendente"
    )
    total_count: int = Field(..., description="Total de registros sin paginar")
    limit: int = Field(..., description="Límite aplicado en la consulta")
    offset: int = Field(..., description="Offset aplicado en la consulta")
    applied_filters: R018Filters = Field(
        ..., description="Filtros usados en la consulta"
    )


class R018TenderItem(BaseModel):
    """Detalle de una licitación que activó R018."""

    release_id: str = Field(..., description="ID del release/licitación")
    title: str | None = Field(None, description="Título de la licitación")
    ocid: str | None = Field(None, description="OCID del procedimiento")
    procurement_method: str = Field(..., description="Método de contratación")
    procedure_date: datetime = Field(
        ..., description="Fecha del procedimiento (cierre o inicio) en formato ISO 8601"
    )
    unique_tenderers: int = Field(
        ..., description="Cantidad de oferentes únicos (siempre 1 para R018)"
    )
    suppliers: str | None = Field(
        None, description="Nombre(s) del proveedor(es) único(s)"
    )
    api_url: str | None = Field(None, description="Enlace a la API con datos completos")


class R018TenderListResponse(BaseModel):
    """Listado de licitaciones R018."""

    data: list[R018TenderItem] = Field(..., description="Lista de licitaciones")
    total_count: int = Field(..., description="Total de registros sin paginar")
    limit: int = Field(..., description="Límite aplicado en la consulta")
    offset: int = Field(..., description="Offset aplicado en la consulta")
    applied_filters: R018Filters = Field(..., description="Filtros utilizados")
