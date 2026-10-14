import threading
import time
import requests
from src.config import settings

_token_cache = {"token": None, "expires_at": 0}
_token_lock = threading.Lock()


def _fetch_token() -> str:
    """Obtiene token nuevo de la API y actualiza el cache."""
    url = f"{settings.dncp_api_base_url}/oauth/token"
    payload = {"request_token": settings.dncp_request_token}
    headers = {"Content-Type": "application/json"}

    resp = requests.post(url, json=payload, headers=headers, timeout=(10, 30))
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    expires_in = data.get("expires_in", 900)  # 15 minutos por defecto
    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + expires_in - 10  # renovar 10s antes
    return token


def get_access_token(force_refresh: bool = False) -> str:
    """Retorna un token válido, lo renueva si expiró"""
    with _token_lock:
        if (
            not force_refresh
            and _token_cache["token"]
            and time.time() < _token_cache["expires_at"]
        ):
            return _token_cache["token"]
        return _fetch_token()
