FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# instala el binario de uv (más rápido que instalarlo con pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# capa cacheable: instala dependencias ANTES de copiar el código,
# así un cambio de código no invalida esta capa en rebuilds
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

CMD sh -c "uv run uvicorn src.interfaces.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-config log_config.yaml"