"""Validación del filtro `year` de la API."""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from src.interfaces.api.dependencies import year_filter


@pytest.fixture(autouse=True)
def _inicio_2020(monkeypatch):
    """Independiza los tests del INDICATORS_START_DATE del .env local."""
    monkeypatch.setattr(
        "src.interfaces.api.dependencies.settings.indicators_start_date", "2020-01-01"
    )


def test_year_none_es_sin_filtro():
    assert year_filter(None) is None


def test_year_dentro_del_rango():
    actual = datetime.now(timezone.utc).year
    assert year_filter(2020) == 2020
    assert year_filter(actual) == actual


@pytest.mark.parametrize("year", [0, 2019, 9999])
def test_year_fuera_de_rango_es_422(year):
    with pytest.raises(HTTPException) as err:
        year_filter(year)
    assert err.value.status_code == 422


def test_year_futuro_es_422():
    with pytest.raises(HTTPException):
        year_filter(datetime.now(timezone.utc).year + 1)
