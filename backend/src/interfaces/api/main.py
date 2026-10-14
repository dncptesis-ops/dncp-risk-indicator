"""
API async (FastAPI + asyncpg).

El sync pesado corre en un proceso separado (src/interfaces/worker.py) y, al
terminar, invalida la caché de /common llamando al endpoint interno
POST /internal/invalidate-cache.
"""

import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.interfaces.api.routers import r018, r063, r064, common
from src.interfaces.api.routers.common import invalidate_common_cache
from src.config import settings
from src.infrastructure.async_db.pool import create_async_pool

# el log lo manejamos en uvicorn con log_config.yaml
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # pool asyncpg para los endpoints de la API
    logger.info("Creando pool de conexiones asyncpg...")
    async_pool = await create_async_pool()
    app.state.async_pool = async_pool  # disponible para las rutas

    if settings.internal_secret == "change-me":
        logger.warning(
            "INTERNAL_SECRET tiene el valor de ejemplo: cualquiera que "
            "lo conozca puede llamar a /internal/invalidate-cache. Cambialo al desplegar."
        )

    logger.info("API started")

    yield

    await async_pool.close()
    logger.info("API shutting down")


app = FastAPI(
    title="OCDS Red Flags API",
    version="1.0.0",
    description="Motor de análisis de riesgos (Red Flags) para datos en formato Open Contracting Data Standard (OCDS).",
    lifespan=lifespan,
)

# CORS: la API es pública y de solo lectura para el navegador (GET, sin
# cookies ni credenciales). Los orígenes se configuran con CORS_ALLOW_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# Exception handler global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones no controladas"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__,
                "path": str(request.url),
                "method": request.method,
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred",
            },
        )


# Endpoint interno: el worker lo llama tras cada sync para invalidar la caché de /common.
@app.post("/internal/invalidate-cache", include_in_schema=False)
async def internal_invalidate_cache(request: Request):
    enviado = request.headers.get("x-internal-secret", "")
    # compare_digest tarda lo mismo acierte o no: no deja adivinar el secreto
    # carácter por carácter midiendo tiempos de respuesta.
    if not hmac.compare_digest(enviado.encode(), settings.internal_secret.encode()):
        raise HTTPException(status_code=403, detail="Forbidden")
    invalidate_common_cache()
    return {"ok": True}


# Registrar routers
app.include_router(r018.router)
app.include_router(r063.router)
app.include_router(r064.router)
app.include_router(common.router)


@app.get("/")
def get_root():
    return {"status": "ok", "message": "OCDS Red Flags API"}
