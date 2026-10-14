from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
import asyncpg
from src.config import settings
from src.core.ports.r018_repository import R018Repository
from src.infrastructure.async_db.r018_repository_impl import AsyncpgR018Repository
from src.core.services.r018_service import R018Service
from src.core.ports.r063_repository import R063Repository
from src.infrastructure.async_db.r063_repository_impl import AsyncpgR063Repository
from src.core.services.r063_service import R063Service
from src.core.ports.r064_repository import R064Repository
from src.infrastructure.async_db.r064_repository_impl import AsyncpgR064Repository
from src.core.services.r064_service import R064Service


async def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.async_pool


def get_r018_repository(pool: asyncpg.Pool = Depends(get_pool)) -> R018Repository:
    return AsyncpgR018Repository(pool)


def get_r018_service(
    repo: R018Repository = Depends(get_r018_repository),
) -> R018Service:
    return R018Service(repo)


def get_r063_repository(pool: asyncpg.Pool = Depends(get_pool)) -> R063Repository:
    return AsyncpgR063Repository(pool)


def get_r063_service(
    repo: R063Repository = Depends(get_r063_repository),
) -> R063Service:
    return R063Service(repo)


def get_r064_repository(pool: asyncpg.Pool = Depends(get_pool)) -> R064Repository:
    return AsyncpgR064Repository(pool)


def get_r064_service(
    repo: R064Repository = Depends(get_r064_repository),
) -> R064Service:
    return R064Service(repo)


# Filtros comunes
MetodoCompetitivo = Literal["open", "selective"]


def year_filter(
    year: int | None = Query(
        None,
        description=(
            "Año del caso. Válido desde el año de INDICATORS_START_DATE hasta el "
            "año actual."
        ),
    ),
) -> int | None:
    """422 si el año está fuera de INDICATORS_START_DATE..hoy."""
    if year is None:
        return None
    minimo = datetime.fromisoformat(settings.indicators_start_date).year
    maximo = datetime.now(timezone.utc).year
    if not minimo <= year <= maximo:
        raise HTTPException(
            status_code=422,
            detail=f"year debe estar entre {minimo} y {maximo}",
        )
    return year
