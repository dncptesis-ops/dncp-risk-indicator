# Sincronización incremental y retención de versiones

Cómo el worker trae los procesos nuevos desde la API de la DNCP, cómo recuerda hasta
dónde llegó y qué hace con las distintas versiones de un mismo proceso.

| Archivo | Qué hace |
|---------|----------|
| `backend/src/interfaces/worker.py` | Ejecuta una sincronización cada determinado tiempo |
| `backend/src/application/sync_service.py` | Ventana de consulta, paginación, punto de control y retención |
| `backend/src/infrastructure/dncp_client.py` | Llamadas a la API (búsqueda y descarga de cada proceso) |
| `backend/src/infrastructure/database.py` | Registro de ejecuciones (`sync_log`) y retención |
| `backend/src/etl/ocds_flatten_ingest.py` | Carga histórica desde CSV |

## 1. Ventana de consulta

El worker guarda un punto de control (*checkpoint*): la fecha del último proceso
que procesó. Se obtiene, en este orden, de:

1. la fecha máxima registrada en `sync_log`;
2. si no hay ejecuciones, la fecha máxima de `releases` (datos cargados por CSV);
3. si no hay nada, `DEFAULT_START_DATE`.

Cada ejecución pide a la API:

```
fecha_desde = checkpoint − 60 minutos
fecha_hasta = momento en que empieza la ejecución (UTC)
```

- 60 minutos hacia atrás porque la búsqueda de la DNCP tiene retraso. Se actualiza
  por tandas, más o menos una vez por hora, y cada tanda agrega los procesos de la
  hora anterior: un proceso tarda entre media hora y hora y media en aparecer
  (medido el 29/09/2026 durante 8 horas con `medir_retraso_busqueda.py`). Ese
  retraso no hace perder procesos: el checkpoint es la fecha del último proceso
  visto, no la hora de la ejecución, y en la medición las tandas llegaron en orden
  de fecha, así que lo que aparece después tiene fecha posterior al checkpoint. Los
  60 minutos son un margen por si una tanda llega incompleta; volver a pedir esa
  franja cuesta poco, porque la carga reemplaza por clave primaria.
- El techo se fija al empezar. Si se dejara abierto, los procesos que cambian
  durante la ejecución se moverían de página y habría repetidos o huecos.
- El checkpoint nunca pasa del inicio de la ejecución. Los procesos se descargan
  después de listarlos. Si uno cambió mientras tanto, trae una fecha posterior; si se
  usara esa fecha, lo publicado en el medio no se pediría nunca. Por eso se recorta.
- Piso móvil y no fijo. Con un piso fijo, cada ejecución recorrería todo desde ese
  piso. Además, pasado el máximo de 10.000 resultados de la API, lo que sobra no se
  vería nunca. Con el piso móvil, una ejecución normal recorre una sola página.

El detalle de cómo la API interpreta las fechas está en
[`api_dncp_fechas_y_limites.md`](api_dncp_fechas_y_limites.md).

## 2. Paginación y repetidos

- Se pide de a 100 resultados por página, ordenados por fecha, hasta la última
  página.
- Un mismo proceso puede aparecer dos veces (por los 60 minutos que se repiten o por
  la paginación). Dentro de una ejecución se procesa una sola vez.

## 3. Punto de control y errores

Cada ejecución queda registrada en `sync_log`, y el progreso se guarda al terminar
cada página.

Si un proceso no se puede cargar, la ejecución no se corta:

1. se sigue con el resto;
2. la ejecución termina como `failed` y guarda los primeros 10 procesos con error;
3. el checkpoint queda en la fecha del proceso que falló, así la siguiente ejecución
   lo vuelve a intentar.

Volver a cargar algo que ya estaba no genera duplicados, porque la carga reemplaza
por clave primaria (*upsert*). Al arrancar, el worker marca como `failed` las
ejecuciones que quedaron a medias (por ejemplo, si se reinició el contenedor).

## 4. Versiones de un proceso y retención

La DNCP republica un proceso cada vez que cambia, y cada versión tiene su
`release_id`. La base guarda solo la versión vigente de cada proceso, no el
historial.

La versión vigente se elige con este orden:

1. la de fecha más reciente;
2. a igual fecha, la descargada por API (el CSV histórico puede venir incompleto:
   el de 2024 trae procesos sin partes);
3. a igual fecha y origen, el `release_id`, para que el resultado sea siempre el
   mismo.

Ese orden se usa en tres lugares:

- Retención: borra las versiones viejas. En la sincronización se aplica al final
  de cada página; en la carga de CSV, una vez al terminar. Al borrar una versión se
  borran en cascada sus partes, licitación, oferentes y contratos.
- Vista `latest_releases`: una fila por proceso. Los indicadores parten de ella,
  así que cuentan cada proceso una vez aunque la retención todavía no haya corrido.
- Vista `party_master`: el nombre más reciente de cada entidad o proveedor.

### Cuánto se descarta

Medido sobre el histórico cargado por CSV (septiembre de 2026):

| | Todas las versiones | Solo la vigente |
|--|---------------------|-----------------|
| Filas en `releases` | 94.780 | 92.298 (una por proceso) |
| Filas en `contracts` | 157.436 | 133.133 |
| Filas en `parties` | 543.193 | 520.090 |
| Entidades con nombre (`party_master`) | 38.752 | 38.731 |

Los indicadores no cambian, porque siempre usaban la versión vigente. El único
costo real son 21 nombres de entidades que solo aparecían en versiones viejas.

## 5. Nombres de entidades (`party_master`)

A veces la versión vigente de un proceso no trae el nombre de una entidad que sí
aparecía en otra versión o en otro proceso. `party_master` guarda, para cada
`party_id`, su nombre más reciente en todo el corpus. Los indicadores usan primero el
nombre de la propia versión y, si falta, el de `party_master`. La vista se actualiza
después de cada sincronización y al final de la carga de CSV.

## 6. Fechas y zona horaria

- Todas las columnas de fecha son `TIMESTAMPTZ` y la base trabaja en UTC.
- Las fechas de la DNCP siempre traen zona horaria. Se comprobó que se guardan sin
  corrimientos (6.431 procesos comparados contra la fecha que la propia DNCP incluye
  en su `release_id`, sin diferencias).
- Años y meses se cortan en UTC. Respecto de la hora de Asunción, eso mueve de mes a
  1 de 71.775 licitaciones y a 2 de 105.966 contratos, y a ninguno de año.
- La web muestra las fechas en hora de Paraguay.

## 7. Comprobaciones útiles

```sql
-- Procesos con más de una versión (debería dar 0 después de la retención)
SELECT COUNT(*) FROM (SELECT ocid FROM releases GROUP BY ocid HAVING COUNT(*) > 1) t;

-- Últimas ejecuciones del worker y punto de control actual
SELECT id, status, records_processed, last_release_date, finished_at, error_message
FROM sync_log ORDER BY id DESC LIMIT 10;
```

```bash
# Pruebas del manejo de fechas y del checkpoint (sin base ni red)
cd backend
uv run python -m src.scripts.v2.probar_fechas_utc
```
