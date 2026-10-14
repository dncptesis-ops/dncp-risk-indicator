import time
from unittest.mock import patch, Mock
import pytest

# Importamos el módulo bajo prueba y la configuración
from src.infrastructure.auth import get_access_token, _token_cache
from src.config import settings


@pytest.fixture(autouse=True)
def setup_settings(monkeypatch):
    """Configura las variables de settings necesarias para las pruebas."""
    monkeypatch.setattr(settings, "dncp_request_token", "fake_request_token")
    monkeypatch.setattr(settings, "dncp_api_base_url", "http://fake-api")


@pytest.fixture(autouse=True)
def reset_token_cache():
    """Reinicia el cache global antes de cada test."""
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0

# 1 - Reemplazamos requests.post por mock_post – así no llamamos a la API real.
# 2 - Configuramos la respuesta falsa con el token "token123".
# 3 - Llamamos a get_access_token().
# 4 - Comprueba: El token devuelto sea exactamente "token123" y que se haya llamado exactamente una vez a requests.post
@patch("src.infrastructure.auth.requests.post")
def test_get_access_token_first_call(mock_post):
    """La primera llamada debe solicitar un token nuevo."""
    mock_response = Mock()
    mock_response.json.return_value = {"access_token": "token123", "expires_in": 900}
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    token = get_access_token()
    assert token == "token123"
    mock_post.assert_called_once()

# llama dos veces seguidas a la función. 
# Comprueba que solo se haga una petición HTTP, demostrando que el token se reutiliza desde la caché.
@patch("src.infrastructure.auth.requests.post")
def test_get_access_token_caches(mock_post):
    """La segunda llamada dentro del tiempo de expiración reutiliza el token."""
    mock_response = Mock()
    mock_response.json.return_value = {"access_token": "token123", "expires_in": 900}
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    token1 = get_access_token()
    token2 = get_access_token()

    assert token1 == "token123"
    assert token2 == "token123"
    # Solo se debe haber llamado una vez a la API
    assert mock_post.call_count == 1

# Avanza el tiempo simulado para que el token caduque. 
# Verifica que se haga una segunda petición y se obtenga un token nuevo.
@patch("src.infrastructure.auth.requests.post")
@patch("src.infrastructure.auth.time.time")
def test_get_access_token_refreshes_when_expired(mock_time, mock_post):
    """Al expirar el token, se pide uno nuevo."""
    # Simulamos el tiempo actual
    current_time = 1000.0
    mock_time.return_value = current_time

    # Token inicial con expiración de 100 segundos
    mock_response = Mock()
    mock_response.json.return_value = {"access_token": "token_old", "expires_in": 100}
    mock_response.raise_for_status = lambda: None
    mock_post.return_value = mock_response

    token1 = get_access_token()
    assert token1 == "token_old"
    assert mock_post.call_count == 1

    # Avanzamos el tiempo para que el token caduque
    # expires_at = time() + expires_in - 10 = 1000 + 100 - 10 = 1090
    # Ponemos el reloj en 1091 (ya expirado)
    current_time = 1091.0
    mock_time.return_value = current_time

    # Configuramos un nuevo token para la siguiente petición
    mock_response.json.return_value = {"access_token": "token_new", "expires_in": 200}
    token2 = get_access_token()
    assert token2 == "token_new"
    assert mock_post.call_count == 2
