# API de la DNCP: fechas, límites y volumen

Cómo se comporta el endpoint `/search/processes` de la API v3 de la DNCP. La
documentación oficial (swagger y portal) no aclara el formato de las fechas, la zona
horaria, si los extremos son inclusivos ni el máximo de resultados, así que todo lo
de este documento se midió contra la API real (septiembre de 2026).

El script `backend/src/scripts/v2/probar_ventana_fechas.py` repite las mediciones
(pruebas P1–P22) y termina con error si alguna propiedad deja de cumplirse. Sirve de
alarma si la DNCP cambia la API.

```bash
cd backend
uv run src/scripts/v2/probar_ventana_fechas.py
```

## 1. Fechas de la consulta

| Propiedad | Ejemplo medido |
|-----------|----------------|
| Un día sin hora abarca el día completo en UTC | `desde=2026-09-05 hasta=2026-09-05` = `[2026-09-05T00:00Z, 2026-09-06T00:00Z]` |
| Se respeta el offset de zona horaria | `2026-08-25T14:58:00-03:00` = `2026-08-25T17:58:00Z` (43 resultados en los dos casos) |
| Los dos extremos son inclusivos | `desde = hasta = <fecha de un release>` devuelve exactamente ese release |
| Ventana vacía o invertida → HTTP 404 | no responde 200 con una lista vacía |
| Sin `fecha_hasta`, equivale a "hasta ahora" | `desde=2026-08-29` sin techo = `hasta=ahora` (1.597 resultados) |
| Sin `tipo_fecha`, la ventana se ignora | responde 200 con el listado completo; con `tipo_fecha=fecha_release` responde lo pedido |
| El filtro usa la última release del proceso | `compiledRelease.date` = la fecha más nueva de sus releases |
| Una fecha mal formada → HTTP 500 | error del servidor, no 400 |

Qué implica para el sistema:

- `fecha_hasta` se manda siempre como instante UTC con hora. Con un día sin hora
  en horario de Asunción, la ventana quedaba recortada o invertida entre las 21:00 y
  las 24:00 locales.
- El 404 no es un error: el cliente lo traduce a "no hay registros nuevos".
- `tipo_fecha=fecha_release` se manda siempre. Sin él, la API ignora la ventana sin
  avisar.
- Las fechas de la DNCP vienen siempre con `-04:00`, también cuando Paraguay estaba
  en UTC-3. El instante igual es correcto (la carga nocturna figura a las
  `23:00-04:00`, medianoche en Paraguay), así que el sistema lo guarda en UTC.
- El índice de búsqueda se actualiza por tandas, más o menos una vez por hora: un
  registro aparece entre media hora y hora y media después de su fecha. Cómo lo
  maneja la sincronización está en
  [`sincronizacion_y_retencion.md`](sincronizacion_y_retencion.md) §1.

## 2. Cuántos resultados devuelve

- Máximo de 10.000 resultados por consulta, sin aviso. Una ventana más grande
  responde HTTP 200 con `total_items = 10000` y el resto se pierde.
- `items_per_page` acepta hasta 1000; si se omite, usa 10. El sistema usa 100.
- El peso de una página depende de los procesos que caen en ella:

  | Tamaño de página | Peso medido |
  |------------------|-------------|
  | 100 resultados | ~112 KB |
  | 1000 resultados | ~2,3 MB, y hasta ~18,6 MB si hay procesos con miles de releases |

  Páginas más grandes implican menos peticiones pero más memoria. Por eso se quedó
  en 100.
- Con el techo de consulta fijo, la paginación es estable: sin repetidos entre
  páginas y en orden de fecha.

## 3. Credenciales y límite de peticiones

| Propiedad | Medición |
|-----------|----------|
| No hace falta credencial | `/search/processes` y `/ocds/record` responden 200 sin token |
| El límite es 15 peticiones por minuto | cabecera `X-RateLimit-Limit: 15` |
| El token no aumenta el límite | 15 con token, sin token y con un token inválido |
| Al pasarse, responde 429 por unos segundos | trae `Retry-After` con la espera sugerida |

El cliente (`dncp_client.py`) ante un 429 espera lo que indica `Retry-After` (hasta
15 minutos, 5 veces como máximo) y reintenta. El contador `X-RateLimit-Remaining`
sube y baja de forma irregular, así que no se usa para planificar.

## 4. Por qué la carga histórica se hace con CSV

Con el máximo de 10.000 resultados y 15 peticiones por minuto, traer todo el
histórico por API no es práctico. Son unos 92.000 procesos, uno por petición, más el
listado: varios días de descarga continua. La DNCP publica los CSV por año
justamente para la carga masiva. Por eso el sistema combina:

1. Carga histórica con los CSV anuales ("procesos completos").
2. Sincronización incremental por API, que trae solo lo nuevo o modificado desde
   el último punto de control. Ver [`sincronizacion_y_retencion.md`](sincronizacion_y_retencion.md).
