from datetime import datetime

from pydantic import BaseModel, Field


class BuyerItem(BaseModel):
    """Entidad compradora."""

    buyer_id: str = Field(..., description="ID del comprador (party_id OCDS)")
    name: str = Field(..., description="Nombre de la entidad")


class BuyersResponse(BaseModel):
    """Lista de entidades compradoras disponibles."""

    data: list[BuyerItem] = Field(
        ..., description="Lista de entidades compradoras ordenadas por nombre"
    )
    total_count: int = Field(..., description="Total de entidades")


class YearsResponse(BaseModel):
    """Lista de años con datos disponibles."""

    years: list[int] = Field(
        ..., description="Años con datos en la BD, ordenados de mayor a menor"
    )


class StatusResponse(BaseModel):
    """Fecha de actualización de los datos."""

    updated_at: datetime | None = Field(
        None,
        description="Última vez que el worker consultó a la DNCP. Si nunca "
        "corrió (solo carga CSV), la fecha del release más reciente.",
    )


class FlaggedContract(BaseModel):
    """Contrato que activó el indicador (R063, R064)."""

    contract_id: str = Field(..., description="Código de contratación (CC) de la DNCP")
    award_id: str | None = Field(
        None, description="ID de la adjudicación; arma el enlace a la ficha del contrato"
    )
