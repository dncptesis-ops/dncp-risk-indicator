# OCDS Red Flags Engine

Backend que calcula indicadores de riesgo (red flags) sobre datos de contratación pública en
formato OCDS.

Trae los procesos de la DNCP (CSV históricos y API), los guarda en PostgreSQL y los expone en una
API REST con KPIs, series mensuales, rankings y listados.

## Indicadores de riesgo

Son tres indicadores de la guía de red flags de Open Contracting Partnership
([OCP, 2024](https://www.open-contracting.org/wp-content/uploads/2024/12/OCP2024-RedFlagProcurement-1.pdf)).
Los tres cuentan por proceso de contratación (un `ocid`, en su versión vigente).

R018, única oferta:
- Evaluados: licitaciones `open` o `selective` con `numberOfTenderers` informado.
- Marcados: `numberOfTenderers = 1`.
- Fecha: fin del período de ofertas (o el inicio si falta).

R063, contrato no publicado:
- Evaluados: procesos con al menos un contrato `active`.
- Marcados: alguno de esos contratos no tiene documento `contractSigned`.
- Fecha: firma del primer contrato activo (o su inicio si falta).

R064, contrato modificado:
- Evaluados: procesos con al menos un contrato `active` o `terminated` (solo un contrato firmado
  puede tener enmiendas).
- Marcados: alguno de esos contratos tiene enmiendas.
- Fecha: firma del primer contrato (o su inicio si falta).

Para los tres:
- Se parte de la vista `latest_releases`, una fila por proceso.
- Solo cuentan fechas entre `INDICATORS_START_DATE` (2020-01-01 por defecto) y hoy. En los datos
  hay fechas imposibles, como 2099.
- Filtros: año y entidad compradora; R018 también método de contratación.
- La entidad compradora es el `buyer` (quien paga). El ranking agrupa por `buyer`; con
  `buyer_id`, muestra las unidades de contratación (`procuringEntity`) de esa entidad. La
  respuesta lo indica en `group_by`.

El código está en `src/infrastructure/async_db/`: un repositorio por indicador y `sql_common.py`
con lo compartido.

## Cómo funciona

1. Carga histórica desde los CSV anuales de la DNCP.
2. Un worker consulta la API de la DNCP cada 6 horas y trae lo nuevo.
3. Los datos quedan en tablas relacionales en PostgreSQL.
4. La API calcula los indicadores.

La lógica trabaja sobre OCDS y la conexión con la DNCP está en un adaptador aparte
(`dncp_client.py`), así que se podría conectar otra fuente OCDS sin cambiar los indicadores.

## Requisitos

- Python 3.13+
- uv (o pip con venv)
- Docker y Docker Compose

## Configuración

```bash
cp .env.example .env
```

Estos son los valores de `.env.example`, en el mismo orden:

| Variable | Valor en `.env.example` | Para qué sirve |
|----------|-------------------------|----------------|
| Base de datos | | |
| `DB_HOST` | `localhost` | Host de PostgreSQL |
| `DB_PORT` | `5432` | Puerto |
| `DB_NAME` | `ocds_data` | Nombre de la base |
| `DB_USER` | `ocds_user` | Usuario (el del PostgreSQL de `docker-compose.local.yml`) |
| `DB_PASSWORD` | `ocds_password` | Contraseña (la del mismo PostgreSQL) |
| `DB_SSLMODE` | `prefer` | Para una base remota con SSL obligatorio, usar `require` |
| Sincronización | | |
| `SYNC_INTERVAL_HOURS` | `6` | Horas entre ejecuciones del worker |
| `DEFAULT_START_DATE` | `2026-01-01` | Desde qué fecha empieza el worker si la base está vacía |
| Adaptador DNCP | | |
| `DNCP_API_BASE_URL` | `https://www.contrataciones.gov.py/datos/api/v3/doc` | URL de la API de la DNCP |
| `DNCP_REQUEST_TOKEN` | (vacío) | Token de la API. No hace falta: la API responde sin token |
| `DNCP_RATE_LIMIT_SLEEP_SECONDS` | `60` | Segundos de espera cuando la API avisa que se pasó el límite de pedidos |
| Motor de sincronización | | |
| `SYNC_MAX_CONCURRENT_REQUESTS` | `3` | Cuántos procesos se descargan en paralelo |
| `SOURCE_TIMEZONE` | `America/Asuncion` | Zona horaria con la que se arma la fecha de inicio de cada consulta |
| Worker -> API | | |
| `INTERNAL_SECRET` | `change-me` | Clave con la que el worker le pide a la API que limpie su caché. Cambiarla al desplegar: la API avisa en el log si sigue en `change-me` |
| `API_INTERNAL_URL` | `http://api:8000` | Dirección de la API vista desde el worker |
| Indicadores | | |
| `INDICATORS_START_DATE` | `2020-01-01` | Solo cuentan casos con fecha entre este día y hoy |
| API | | |
| `CORS_ALLOW_ORIGINS` | `*` | Desde qué sitios se puede llamar a la API. En producción, poner la URL del frontend (varias, separadas por coma) |
| Debug | | |
| `DEBUG` | `false` | Con `true`, la API devuelve el detalle del error en las respuestas 500 |
| `DEBUG_FLATTEN_OUTPUT` | `false` | Con `true`, el sync guarda en disco los CSV aplanados de cada record |
| `DEBUG_FLATTEN_DIR` | `data/debug_flatten` | Carpeta donde se guardan esos CSV |

Si una variable falta en el `.env`, se usa el valor de `src/config.py`. `PORT` no está en
`.env.example`: es el puerto de la API dentro del contenedor y por defecto es `8000`.

## Ejecución

### Primera vez (base vacía)

El orden importa: primero se carga el histórico de los CSV y recién después se levanta el
worker. Si el worker arranca con la base vacía, empieza a bajar todo por la API desde
`DEFAULT_START_DATE`, que es lento (la API permite 15 pedidos por minuto) y no trae el histórico.

1. Configurar e instalar dependencias:

```bash
cp .env.example .env
uv sync
# sin uv: python3.13 -m venv .venv && source .venv/bin/activate && pip install -e .
```

2. Levantar solo la base de datos. La primera vez se crea con `schema.sql`:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d db

# ver que se crearon las tablas
docker exec -t ocds_postgres_db psql -U ocds_user -d ocds_data -c "\dt"
```

3. Cargar el histórico. Los CSV se bajan del portal de datos abiertos de la DNCP (procesos
   completos, un zip por año) y cada año va en su carpeta (`2020/`, `2021/`, ...). Ver
   [Carga histórica](#carga-histórica-csv).

```bash
uv run python -m src.etl.ocds_flatten_ingest --data-dir data/historical --recursive --year-from 2020 --year-to 2026
```

4. Volver a bajar por la API los procesos que el CSV trae sin partes:

```bash
uv run python -m src.scripts.v2.reparar_partes_faltantes --aplicar
```

5. Levantar la API y el worker. El worker sigue desde la fecha más reciente cargada.

```bash
# con Docker
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build

# o sin Docker, cada uno en su terminal
uv run uvicorn src.interfaces.api.main:app --host 0.0.0.0 --port 8000 --reload   # API
uv run python -m src.interfaces.worker                                          # worker
```

### Las siguientes veces

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

Levanta `ocds_postgres_db` (PostgreSQL), `ocds_api` (API en `:8000`) y `ocds_etl_worker`
(sincronización cada 6 horas). El worker sigue desde donde quedó la última ejecución (`sync_log`).

Para levantar solo la base de datos (por ejemplo, para ejecutar la API o un script desde la
máquina):

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d db
```

## API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Estado del servicio |
| `GET` | `/common/buyers` | Entidades compradoras |
| `GET` | `/common/years` | Años con datos |
| `GET` | `/common/status` | Fecha de la última actualización |
| `GET` | `/r018/kpi`, `/r018/monthly` | KPI y serie mensual |
| `GET` | `/r018/top-entities`, `/r018/suppliers` | Ranking de entidades y de proveedores |
| `GET` | `/r018/tenders` | Licitaciones con un solo oferente |
| `GET` | `/r063/kpi`, `/r063/monthly`, `/r063/top-entities` | KPI, serie y ranking |
| `GET` | `/r063/processes` | Procesos marcados |
| `GET` | `/r064/kpi`, `/r064/monthly`, `/r064/top-entities` | KPI, serie y ranking |
| `GET` | `/r064/processes` | Procesos marcados |
| `POST` | `/internal/invalidate-cache` | Lo llama el worker (cabecera `x-internal-secret`) |

Todos los endpoints de indicadores aceptan `year` y `buyer_id`; los de R018 también
`proc_method` (`open` o `selective`) y `/r018/tenders` también `supplier_id`. Los rankings y
listados se paginan con `limit` y `offset`. Un `year` fuera de rango o un `proc_method` inválido
responden 422.

Swagger: `http://localhost:8000/docs`. En
[`docs/dncp-risk-indicator-bruno/`](docs/dncp-risk-indicator-bruno/) hay una colección de Bruno
con ejemplos.

## Carga histórica (CSV)

Es el paso 3 del primer arranque. Se corre desde la máquina (con `uv`) contra la base del
contenedor.

```bash
# un año
uv run python -m src.etl.ocds_flatten_ingest --data-dir data/2024
# todas las subcarpetas de años
uv run python -m src.etl.ocds_flatten_ingest --data-dir data/historical --recursive
# un rango de años
uv run python -m src.etl.ocds_flatten_ingest --data-dir data/historical --recursive --year-from 2020 --year-to 2026
```

Con `--recursive`, cada subcarpeta se tiene que llamar como el año. El ETL usa estos archivos de
la DNCP:

| Archivo | Tablas |
|---------|--------|
| `records.csv` | `releases`, `tender` |
| `parties.csv` | `parties`, `party_roles` |
| `ten_tenderers.csv` | `tenderers` |
| `contracts.csv` | `contracts` |
| `con_documents.csv` | `contract_documents` |
| `con_amendments.csv` | `contract_amendments` |

No vuelve a procesar un archivo que no cambió (guarda su MD5 en `etl_runs`) y hace upsert por
clave primaria. Al terminar deja una sola versión por `ocid` y refresca `party_master`. Ver
[`../docs/`](../docs/).

Después de la carga hay que ejecutar `reparar_partes_faltantes` (paso 4): el CSV de 2024 trae
procesos sin partes que la API sí tiene.

## Modelo de datos

| Grupo | Tablas |
|-------|--------|
| Control | `etl_runs`, `sync_log` |
| Proceso | `releases` |
| Partes | `parties`, `party_roles` |
| Licitación | `tender`, `tenderers` |
| Contratos | `contracts`, `contract_amendments`, `contract_documents` |

Vistas:
- `latest_releases`: la versión vigente de cada proceso. Los indicadores parten de acá.
- `party_master` (materializada): el nombre más reciente de cada entidad, para cuando la versión
  vigente no lo trae.

El esquema está en `schema.sql` (se genera con `create_schema.py`) y se aplica al crear la base.

## Scripts

```bash
# genera schema.sql
uv run src/scripts/v2/create_schema.py

# pruebas contra la API real de la DNCP (fechas, límites, paginación)
uv run src/scripts/v2/probar_ventana_fechas.py

# pruebas del manejo de zona horaria del sync (sin red ni base)
uv run python -m src.scripts.v2.probar_fechas_utc

# cuánto tarda un proceso en aparecer en la búsqueda de la DNCP (deja un CSV en data/)
uv run python -m src.scripts.v2.medir_retraso_busqueda --horas 8

# cobertura de los campos que pide OCP para cada indicador (hipótesis secundaria)
uv run python -m src.scripts.v2.medir_cobertura_campos

# procesos sin partes después de la carga CSV: los vuelve a bajar de la API
uv run python -m src.scripts.v2.reparar_partes_faltantes            # solo informa
uv run python -m src.scripts.v2.reparar_partes_faltantes --aplicar  # repara
```

Lo que miden los scripts está en
[`../docs/api_dncp_fechas_y_limites.md`](../docs/api_dncp_fechas_y_limites.md) y
[`../docs/sincronizacion_y_retencion.md`](../docs/sincronizacion_y_retencion.md).

## Tests

```bash
uv run pytest
```

Hay dos grupos:

- Unitarios (`tests/application`, `tests/etl`, `tests/infrastructure`, `tests/interfaces`):
  con mocks, sin base ni red. Cubren el cliente de la DNCP (autenticación, límite de pedidos,
  reintentos), el repositorio de la base (`sync_log`, checkpoint, retención, upsert), la
  sincronización (ventana, repetidos, records con error, checkpoint), el ETL y los filtros de la
  API.
- Con datos controlados (`tests/integration`): un conjunto de procesos armado a mano, en CSV
  con las columnas de la DNCP (`datos_controlados.py`), con el resultado esperado de cada
  indicador calculado a mano. Se carga con el ETL real en una base PostgreSQL temporal y se
  compara con lo que devuelve la API (KPI, serie mensual, rankings, listados y catálogos).

Las pruebas con datos controlados necesitan la base local levantada
(`docker compose -f docker-compose.yml -f docker-compose.local.yml up -d db`). Crean una base
nueva y la borran al terminar; no usan el `.env`. Si no hay PostgreSQL local, se saltean. Para
usar otro servidor: `TEST_DATABASE_URL=postgresql://usuario:clave@host:5432/base`.

## Dependencias

- FastAPI y uvicorn: API
- asyncpg: PostgreSQL desde la API
- psycopg2-binary: PostgreSQL desde el worker y el ETL
- pandas: ETL
- flattentool: aplanado de los records OCDS
- pydantic y pydantic-settings: modelos y configuración
- requests: cliente de la API de la DNCP
- pyyaml: configuración de logs
