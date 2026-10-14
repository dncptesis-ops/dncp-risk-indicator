import logging
import threading
import time
import requests
from src.config import settings
from src.infrastructure.auth import get_access_token

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = (10, 60)  # (connect, read) en segundos
MAX_RATE_LIMIT_SLEEP = 15 * 60  # nunca dormir más de 15 min de una

# Reintentos separados: un 429 o un 401 no gastan los intentos de errores de red / 5xx.
MAX_ERROR_ATTEMPTS = 3  # errores de red y respuestas 5xx
MAX_RATE_LIMIT_WAITS = 5  # esperas ante 429
MAX_AUTH_REFRESHES = 2  # renovaciones de token ante 401


class DNCPClient:
    def __init__(self, base_url=None, rate_limit_sleep=None, timeout=DEFAULT_TIMEOUT):
        self.base_url = base_url or settings.dncp_api_base_url
        self.rate_limit_sleep = (
            rate_limit_sleep or settings.dncp_rate_limit_sleep_seconds
        )
        self.timeout = timeout
        # una Session por thread para reutilizar la conexion
        self._local = threading.local()

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
        return session

    def _get_headers(self, force_refresh: bool = False):
        token = get_access_token(force_refresh=force_refresh)
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def _check_rate_limit(self, response):
        """Si quedan 0 o 1 peticiones, espera hasta el reset."""
        remaining = response.headers.get("X-Ratelimit-Remaining")
        if remaining is None:
            return
        try:
            remaining = int(remaining)
        except (TypeError, ValueError):
            return
        if remaining <= 1:
            wait_time = self.rate_limit_sleep
            reset_ts = response.headers.get("X-Ratelimit-Reset")
            if reset_ts:
                try:
                    wait_time = max(float(reset_ts) - time.time(), 0) + 1
                except (TypeError, ValueError):
                    wait_time = self.rate_limit_sleep
            wait_time = min(wait_time, MAX_RATE_LIMIT_SLEEP)
            logger.info(f"Rate limit: durmiendo {wait_time:.0f}s")
            time.sleep(wait_time)

    def _sleep_for_rate_limit(self, response):
        """Ante un 429 siempre espera (Retry-After o rate_limit_sleep)."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                wait_time = float(retry_after)
            except (TypeError, ValueError):
                wait_time = self.rate_limit_sleep
        else:
            wait_time = self.rate_limit_sleep
            reset_ts = response.headers.get("X-Ratelimit-Reset")
            if reset_ts:
                try:
                    wait_time = max(wait_time, float(reset_ts) - time.time() + 1)
                except (TypeError, ValueError):
                    pass
        wait_time = max(min(wait_time, MAX_RATE_LIMIT_SLEEP), 0)
        logger.info(f"Rate limit (429): durmiendo {wait_time:.0f}s")
        time.sleep(wait_time)

    def _request(self, method, url, **kwargs):
        """GET/POST con reintentos para red/5xx, 429 y 401 por separado."""
        headers = self._get_headers()
        kwargs.setdefault("headers", {}).update(headers)
        kwargs.setdefault("timeout", self.timeout)

        error_attempts = 0
        rate_limit_waits = 0
        auth_refreshes = 0

        while True:
            try:
                resp = self._session().request(method, url, **kwargs)
            except requests.RequestException as e:
                error_attempts += 1
                if error_attempts >= MAX_ERROR_ATTEMPTS:
                    raise RuntimeError(
                        f"Falló la petición tras {error_attempts} errores de red: {url}"
                    ) from e
                wait = 2 ** (error_attempts - 1)
                logger.warning(
                    f"Error de red (intento {error_attempts}/{MAX_ERROR_ATTEMPTS}) "
                    f"en {url}: {e}. Reintento en {wait}s"
                )
                time.sleep(wait)
                continue

            if resp.status_code == 429:
                rate_limit_waits += 1
                if rate_limit_waits > MAX_RATE_LIMIT_WAITS:
                    raise RuntimeError(
                        f"Rate limit persistente tras {MAX_RATE_LIMIT_WAITS} "
                        f"esperas: {url}"
                    )
                self._sleep_for_rate_limit(resp)
                continue

            if resp.status_code == 401:
                auth_refreshes += 1
                if auth_refreshes > MAX_AUTH_REFRESHES:
                    raise RuntimeError(
                        f"Autenticación rechazada tras {MAX_AUTH_REFRESHES} "
                        f"renovaciones de token: {url}"
                    )
                # Forzar renovación del token de forma thread-safe
                kwargs["headers"].update(self._get_headers(force_refresh=True))
                continue

            if resp.status_code >= 500:
                error_attempts += 1
                if error_attempts >= MAX_ERROR_ATTEMPTS:
                    raise RuntimeError(
                        f"Falló la petición tras {error_attempts} respuestas "
                        f"{resp.status_code}: {url}"
                    )
                wait = 2 ** (error_attempts - 1)
                logger.warning(
                    f"Error {resp.status_code} del servidor "
                    f"(intento {error_attempts}/{MAX_ERROR_ATTEMPTS}) en {url}. "
                    f"Reintento en {wait}s"
                )
                time.sleep(wait)
                continue

            self._check_rate_limit(resp)
            resp.raise_for_status()
            data = resp.json()
            size = len(resp.content) if isinstance(resp.content, (bytes, bytearray)) else None
            logger.info(f"Respuesta {method} {url}: {size} bytes")
            return data

    def search_processes(
        self,
        fecha_desde: str,
        fecha_hasta: str | None = None,
        page: int = 1,
        items_per_page: int = 50,
    ) -> dict:
        """Busca procesos con cambios entre fecha_desde y fecha_hasta (inclusive).

        Sin tipo_fecha la API ignora las fechas, por eso va siempre. Si no hay
        resultados responde 404. Ver docs/api_dncp_fechas_y_limites.md.
        """
        params = {
            "fecha_desde": fecha_desde,
            "tipo_fecha": "fecha_release",
            "page": page,
            "items_per_page": items_per_page,
            "order": "date asc",
        }
        if fecha_hasta:
            params["fecha_hasta"] = fecha_hasta
        url = f"{self.base_url}/search/processes"
        logger.debug(f"GET {url} params={params}")

        try:
            return self._request("GET", url, params=params)
        except requests.exceptions.HTTPError as e:
            # si no hay registros, la dncp devuelve status 404
            if e.response is not None and e.response.status_code == 404:
                return {"records": []}
            raise

    def get_record(self, ocid: str) -> dict:
        """Obtiene el Record Package completo desde /ocds/record/{ocid}."""
        url = f"{self.base_url}/ocds/record/{ocid}"
        return self._request("GET", url)
