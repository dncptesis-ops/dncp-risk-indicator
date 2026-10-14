from unittest.mock import patch, Mock

import pytest

from src.infrastructure.dncp_client import (
    DNCPClient,
    MAX_AUTH_REFRESHES,
    MAX_ERROR_ATTEMPTS,
    MAX_RATE_LIMIT_WAITS,
)


@pytest.fixture
def client():
    return DNCPClient(base_url="http://fake-api", rate_limit_sleep=0.1)


@patch("src.infrastructure.dncp_client.get_access_token", return_value="fake-token")
@patch("requests.Session.request")
def test_search_processes_success(mock_request, mock_token, client):
    """Verifica la llamada GET a /search/processes con los parámetros correctos."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = {"records": [], "pagination": {}}
    mock_request.return_value = mock_response

    result = client.search_processes("2025-01-01", page=2, items_per_page=10)

    mock_request.assert_called_once_with(
        "GET",
        "http://fake-api/search/processes",
        params={
            "fecha_desde": "2025-01-01",
            "tipo_fecha": "fecha_release",
            "page": 2,
            "items_per_page": 10,
            "order": "date asc",
        },
        headers={"Authorization": "Bearer fake-token", "Accept": "application/json"},
        timeout=(10, 60),
    )
    assert result == {"records": [], "pagination": {}}


@patch("src.infrastructure.dncp_client.get_access_token", return_value="old-token")
@patch("requests.Session.request")
def test_retry_on_401_and_refresh_token(mock_request, mock_token):
    """Cuando recibe 401, fuerza renovación del token y reintenta."""
    mock_401 = Mock(status_code=401, headers={})
    mock_200 = Mock(status_code=200, headers={})
    mock_200.json.return_value = {"release": "ok"}
    mock_request.side_effect = [mock_401, mock_200]

    client = DNCPClient(base_url="http://fake-api")
    result = client.get_record("ocds-1")

    assert mock_request.call_count == 2
    assert mock_token.call_count >= 2 
    assert result == {"release": "ok"}


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token-ratelimit")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("src.infrastructure.dncp_client.time.time")
@patch("requests.Session.request")
def test_rate_limit_when_remaining_low(mock_request, mock_time, mock_sleep, mock_token):
    """Si X-Ratelimit-Remaining <= 1, espera hasta el reset."""
    mock_time.return_value = 1000.0
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {
        "X-Ratelimit-Remaining": "0",
        "X-Ratelimit-Reset": "1030.0",
    }
    mock_response.json.return_value = {"data": "ok"}
    mock_request.return_value = mock_response

    client = DNCPClient(base_url="http://fake-api", rate_limit_sleep=60)
    result = client.search_processes("2025-01-01")

    mock_sleep.assert_called_once_with(31.0)
    assert result == {"data": "ok"}


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("requests.Session.request")
def test_retry_on_429(mock_request, mock_sleep, mock_token):
    """En 429, espera el Retry-After indicado."""
    mock_429 = Mock(status_code=429, headers={"Retry-After": "5"})
    mock_200 = Mock(status_code=200, headers={})
    mock_200.json.return_value = {"data": "ok"}
    mock_request.side_effect = [mock_429, mock_200]

    client = DNCPClient(base_url="http://fake-api")
    result = client.get_record("ocds-1")

    mock_sleep.assert_called_once_with(5)
    assert mock_request.call_count == 2
    assert result == {"data": "ok"}


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("requests.Session.request")
def test_retry_on_5xx(mock_request, mock_sleep, mock_token):
    """En 5xx, reintenta con backoff."""
    mock_500 = Mock(status_code=500, headers={})
    mock_200 = Mock(status_code=200, headers={})
    mock_200.json.return_value = {"data": "ok"}
    mock_request.side_effect = [mock_500, mock_200]

    client = DNCPClient(base_url="http://fake-api")
    result = client.get_record("ocds-1")

    assert mock_request.call_count == 2
    mock_sleep.assert_called_once_with(1)
    assert result == {"data": "ok"}


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("requests.Session.request")
def test_429_y_401_no_consumen_el_presupuesto_de_errores(
    mock_request, mock_sleep, mock_token
):
    """429 + 401 + un 5xx transitorio deben terminar bien.

    Con el presupuesto compartido anterior la petición se agotaba antes de
    llegar siquiera a un intento "limpio".
    """
    r429 = Mock(status_code=429, headers={"Retry-After": "1"})
    r401 = Mock(status_code=401, headers={})
    r500 = Mock(status_code=500, headers={})
    r200 = Mock(status_code=200, headers={})
    r200.json.return_value = {"data": "ok"}
    mock_request.side_effect = [r429, r401, r500, r200]

    client = DNCPClient(base_url="http://fake-api")
    result = client.get_record("ocds-1")

    assert mock_request.call_count == 4
    assert result == {"data": "ok"}


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("requests.Session.request")
def test_429_sin_retry_after_duerme_al_menos_el_minimo(
    mock_request, mock_sleep, mock_token
):
    """Un 429 con X-Ratelimit-Remaining >= 2 no debe reintentar de inmediato."""
    r429 = Mock(status_code=429, headers={"X-Ratelimit-Remaining": "5"})
    r200 = Mock(status_code=200, headers={})
    r200.json.return_value = {"data": "ok"}
    mock_request.side_effect = [r429, r200]

    client = DNCPClient(base_url="http://fake-api", rate_limit_sleep=60)
    result = client.get_record("ocds-1")

    mock_sleep.assert_called_once_with(60)
    assert result == {"data": "ok"}


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("requests.Session.request")
def test_agota_el_presupuesto_de_errores(mock_request, mock_sleep, mock_token):
    """Tras MAX_ERROR_ATTEMPTS respuestas 5xx la petición falla."""
    mock_request.return_value = Mock(status_code=500, headers={})

    client = DNCPClient(base_url="http://fake-api")
    with pytest.raises(RuntimeError):
        client.get_record("ocds-1")

    assert mock_request.call_count == MAX_ERROR_ATTEMPTS


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("requests.Session.request")
def test_agota_el_presupuesto_de_refrescos_de_token(
    mock_request, mock_sleep, mock_token
):
    """401 repetidos: se corta tras MAX_AUTH_REFRESHES renovaciones."""
    mock_request.return_value = Mock(status_code=401, headers={})

    client = DNCPClient(base_url="http://fake-api")
    with pytest.raises(RuntimeError):
        client.get_record("ocds-1")

    assert mock_request.call_count == MAX_AUTH_REFRESHES + 1


@patch("src.infrastructure.dncp_client.get_access_token", return_value="token")
@patch("src.infrastructure.dncp_client.time.sleep")
@patch("requests.Session.request")
def test_agota_el_presupuesto_de_esperas_de_rate_limit(
    mock_request, mock_sleep, mock_token
):
    """429 repetidos: se corta tras MAX_RATE_LIMIT_WAITS esperas."""
    mock_request.return_value = Mock(status_code=429, headers={"Retry-After": "1"})

    client = DNCPClient(base_url="http://fake-api")
    with pytest.raises(RuntimeError):
        client.get_record("ocds-1")

    assert mock_request.call_count == MAX_RATE_LIMIT_WAITS + 1


@patch("src.infrastructure.dncp_client.requests.Session")
def test_reutiliza_la_sesion_en_el_mismo_thread(mock_session_cls):
    """Se crea una sola Session por thread (pooling de conexiones)."""
    client = DNCPClient(base_url="http://fake-api")

    assert client._session() is client._session()
    assert mock_session_cls.call_count == 1
