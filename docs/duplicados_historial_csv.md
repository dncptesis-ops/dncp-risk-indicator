# Procesos con dos versiones en el histórico CSV

## Qué pasa

En el histórico cargado desde los CSV anuales de la DNCP, 2.482 procesos tienen
dos versiones: 94.780 filas de `releases` para 92.298 procesos distintos. Ninguno
tiene más de dos (medido sobre 2020–2026).

No es un error de carga. La clave de `releases` es `release_id`, y cada versión de un
proceso tiene su propio `release_id`.

## Por qué

El `release_id` de la DNCP termina con el momento (*epoch*) en que se generó esa
versión. Aparecen varios formatos:

| Formato | Ejemplo |
|---------|---------|
| número-texto-epoch | `371277-modificacion-sistema-filtracion-agua-...-1578565814` |
| número-epoch con decimales | `337701-1670322452.15173` |
| número-texto-epoch con decimales | `260905-empresas-constructoras-...-1778238361.995` |
| con fecha y zona horaria en lugar de epoch | `…-2026-09-04T11:12:39-04:00` |

Las dos versiones de un proceso salen de dos situaciones:

1. El proceso se republicó en otro momento. Es lo mismo que ve el worker cuando
   la DNCP actualiza un proceso. Por ejemplo, `ocds-03ad3f-260905-1` tiene una
   versión de 2024-04-30 y otra de 2026-05-08.
2. Exportaciones masivas. Hay un mismo epoch compartido por miles de registros
   (`1670322452.15173`, del 2022-12-06, en 17.817 releases). Los CSV históricos
   acumulan varias exportaciones, no son una sola foto.

En los 2.482 casos, las dos versiones tienen fecha y `release_id` distintos.

## Cómo se resuelve

La retención deja solo la versión vigente de cada proceso: la de fecha más reciente
y, a igual fecha, la descargada por API. Se aplica al final de la carga histórica y
en cada página del worker. Ver
[`sincronizacion_y_retencion.md`](sincronizacion_y_retencion.md) §4.

Los indicadores no cambian: parten de la vista `latest_releases`, que ya elige la
versión vigente.

## Cómo comprobarlo

```sql
-- Procesos con más de una versión (debería dar 0 después de la retención)
SELECT COUNT(*) FROM (SELECT ocid FROM releases GROUP BY ocid HAVING COUNT(*) > 1) t;

-- Epochs más repetidos (exportaciones masivas)
SELECT substring(release_id from '[0-9]+\.[0-9]+$') AS epoch, COUNT(*) AS releases
FROM releases GROUP BY 1 ORDER BY releases DESC LIMIT 10;
```
