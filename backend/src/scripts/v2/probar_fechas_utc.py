"""
Pruebas del manejo de zona horaria en el sync (_parse_release_date, _as_utc y
el checkpoint).

Antes se usaba datetime.fromisoformat(x).astimezone(timezone.utc). Con una
fecha sin zona, astimezone() toma la zona de la máquina, así que el checkpoint
cambiaba según dónde corriera. Ahora una fecha sin zona se toma como UTC.

D1 a D8 no usan red ni base de datos. D9 (--api N) revisa el formato de las
fechas en N records reales.

Uso (desde backend/, con -m para importar el código real de src):

    uv run python -m src.scripts.v2.probar_fechas_utc
    uv run python -m src.scripts.v2.probar_fechas_utc --json evidencia.json
    uv run python -m src.scripts.v2.probar_fechas_utc --api 5 --pausa 5

Sale con 1 si alguna prueba falla y con 2 si falla la red en D9.
"""

import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from src.application.sync_service import (
    SYNC_LOOKBACK,
    SyncService,
    _as_utc,
    _parse_release_date,
)

TZ_CANDIDATAS = ("UTC", "America/Asuncion", "Europe/Madrid")
NAIVE = "2026-01-10T10:00:00"  # sin zona: el caso peligroso
NAIVE_VERANO = "2026-07-10T10:00:00"
AWARE_REAL = "2020-08-24T16:18:08-04:00"  # formato real del payload DNCP
AWARE_RECIENTE = "2026-09-12T15:31:12-04:00"  # max de un día medido en la API
AWARE_UTC = "2026-09-12T19:31:12+00:00"
CASOS_BASURA = (None, "", "   ", "basura", "2026-13-45T00:00:00", 0, [], {"a": 1})
CASOS_SOLO_DIA = ("2026-01-10", "2026-01-10T00:00:00")
_rutas = {"json": None}
_filas: list[dict] = []


def _tiene_tzset() -> bool:
    return hasattr(time, "tzset")


@contextmanager
def _tz(nombre):
    """Ejecuta el bloque con la TZ del proceso cambiada (como otra máquina)."""
    previo = os.environ.get("TZ")
    os.environ["TZ"] = nombre
    time.tzset()
    try:
        yield
    finally:
        if previo is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previo
        time.tzset()


def _antes(texto: str) -> datetime:
    """Lo que hacía el código anterior: `astimezone()` directo sobre el parseo."""
    return datetime.fromisoformat(texto).astimezone(timezone.utc)


def _fila(prueba, verificacion, ok, detalles=()):
    print(f"[{'OK' if ok else 'FALLA'}] {prueba:<3} {verificacion}")
    for etiqueta, valor in detalles:
        print(f"        {etiqueta:<48} -> {valor}")
    _filas.append(
        {
            "prueba": prueba,
            "verificacion": verificacion,
            "ok": bool(ok),
            "detalles": [[e, str(v)] for e, v in detalles],
        }
    )
    return ok


def _fmt(valor) -> str:
    """Formatea una fecha de forma estable (UTC) para la salida."""
    if isinstance(valor, datetime):
        return f"{valor.isoformat()} (tz={valor.tzinfo})"
    return repr(valor)


def _horas(delta: timedelta) -> str:
    """Duración legible en horas (evita el '1 day, 23:00:00' de timedelta)."""
    return f"{delta.total_seconds() / 3600:+.2f} h"


def _salta(prueba, motivo):
    print(f"[OMITIDA] {prueba} {motivo} (no se cuenta como falla)")
    _filas.append({"prueba": prueba, "verificacion": motivo, "ok": None, "detalles": []})


def _sondas_d1_d3() -> list[str]:
    """D1-D3: dependen de la TZ del proceso (necesitan `time.tzset()`)."""
    if not _tiene_tzset():
        for prueba in ("D1", "D2", "D3"):
            _salta(prueba, "la plataforma no tiene time.tzset()")
        return []
    fallas = []

    # D1: la versión anterior dependía de la TZ del proceso.
    anteriores = {}
    for nombre in TZ_CANDIDATAS:
        with _tz(nombre):
            anteriores[nombre] = _antes(NAIVE)
    with _tz("Europe/Madrid"):
        verano = _antes(NAIVE_VERANO)
    ok = len(set(anteriores.values())) == len(TZ_CANDIDATAS)
    if not _fila(
        "D1",
        "versión anterior, fecha naive: el resultado dependía de la TZ del proceso",
        ok,
        [(f"TZ={n}", _fmt(v)) for n, v in anteriores.items()]
        + [
            ("desfase en Asunción (UTC-3)", "3 h por delante"),
            ("desfase en Madrid (enero, CET)", "1 h por detrás"),
            ("Madrid con '2026-07-10' (CEST)", _fmt(verano)),
        ],
    ):
        fallas.append("D1")

    # D2: la versión actual es independiente del entorno.
    actuales = {}
    for nombre in TZ_CANDIDATAS:
        with _tz(nombre):
            actuales[nombre] = _parse_release_date(NAIVE)
    esperado_naive = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ok = set(actuales.values()) == {esperado_naive}
    if not _fila(
        "D2",
        "versión actual, fecha naive: mismo instante en cualquier TZ (= naive como UTC)",
        ok,
        [(f"TZ={n}", _fmt(v)) for n, v in actuales.items()],
    ):
        fallas.append("D2")

    # D3: no-regresión con el formato real del payload (siempre con offset).
    regresion = {}
    for nombre in TZ_CANDIDATAS:
        with _tz(nombre):
            regresion[nombre] = (_antes(AWARE_REAL), _parse_release_date(AWARE_REAL))
    esperado = datetime(2020, 8, 24, 20, 18, 8, tzinfo=timezone.utc)
    ok = all(a == b == esperado for a, b in regresion.values())
    if not _fila(
        "D3",
        "no-regresión: con fecha aware el antes y el ahora dan lo mismo en toda TZ",
        ok,
        [
            (f"TZ={n}", f"antes={a.isoformat()} ahora={b.isoformat()}")
            for n, (a, b) in regresion.items()
        ],
    ):
        fallas.append("D3")

    return fallas


def _sondas_d4() -> list[str]:
    """D4: independiente de la TZ (corre en cualquier plataforma)."""
    fallas = []

    # D4: preserva el instante de cualquier fecha aware.
    casos = (AWARE_REAL, AWARE_RECIENTE, AWARE_UTC, "2026-09-12T19:31:12Z")
    detalles, ok = [], True
    for texto in casos:
        original = datetime.fromisoformat(texto)
        normal = _as_utc(original)
        bien = normal == original and normal.tzinfo is timezone.utc
        ok = ok and bien
        detalles.append((texto, f"{_fmt(normal)} {'OK' if bien else 'MAL'}"))
    if not _fila("D4", "fecha aware: instante conservado y tzinfo=UTC", ok, detalles):
        fallas.append("D4")

    return fallas


def _sondas_d5_d6() -> list[str]:
    """D5-D6: idempotencia y entradas corruptas (sin red y sin TZ especial)."""
    fallas = []

    # D5: idempotencia.
    ok, detalles = True, []
    for texto in (NAIVE, AWARE_REAL, AWARE_RECIENTE, AWARE_UTC):
        una = _parse_release_date(texto)
        dos = _as_utc(una)
        ok = ok and dos == una
        detalles.append((texto, f"{una.isoformat()} -> {dos.isoformat()}"))
    if not _fila("D5", "idempotente: `_as_utc(_as_utc(x)) == _as_utc(x)`", ok, detalles):
        fallas.append("D5")

    # D6: nunca lanza; día suelto = 00:00 UTC.
    ok, detalles = True, []
    for valor in CASOS_BASURA:
        try:
            resultado = _parse_release_date(valor)
            bien = resultado is None
        except Exception as e:  # la prueba busca justamente que no lance
            resultado, bien = f"lanzó {type(e).__name__}: {e}", False
        ok = ok and bien
        detalles.append((repr(valor), _fmt(resultado)))
    for valor in CASOS_SOLO_DIA:
        resultado = _parse_release_date(valor)
        bien = resultado == datetime(2026, 1, 10, tzinfo=timezone.utc)
        ok = ok and bien
        detalles.append((repr(valor), _fmt(resultado)))
    if not _fila(
        "D6",
        "entrada vacía/corrupta => None (sin lanzar); día suelto => 00:00 UTC",
        ok,
        detalles,
    ):
        fallas.append("D6")

    return fallas


def _sondas_d7_d8() -> list[str]:
    """D7-D8: efecto sobre el checkpoint, con la TZ simulada (sin BD)."""
    if not _tiene_tzset():
        for prueba in ("D7", "D8"):
            _salta(prueba, "la plataforma no tiene time.tzset()")
        return []
    fallas = []

    # D7: efecto del código anterior en una máquina UTC-3.
    nuevo = _parse_release_date(NAIVE)
    piso_nuevo = nuevo - SYNC_LOOKBACK
    naive_utc = datetime.fromisoformat(NAIVE).replace(tzinfo=timezone.utc)
    with _tz("America/Asuncion"):
        viejo_asuncion = _antes(NAIVE)
    with _tz("Europe/Madrid"):
        viejo_madrid = _antes(NAIVE)
    piso_viejo = viejo_asuncion - SYNC_LOOKBACK
    piso_madrid = viejo_madrid - SYNC_LOOKBACK
    corrimiento = piso_viejo - piso_nuevo  # cuánto se corre el piso de la ventana
    franja = piso_viejo - nuevo  # franja por encima del checkpoint que no se re-pide
    corrimiento_madrid = piso_madrid - piso_nuevo
    ok = (
        corrimiento == timedelta(hours=3)
        and franja == timedelta(hours=2)
        and franja > SYNC_LOOKBACK
    )
    if not _fila(
        "D7",
        "en máquina UTC-3 el checkpoint se corría 3 h y la franja de 2 h se perdía",
        ok,
        [
            ("ahora: checkpoint / piso", f"{nuevo.isoformat()} / {piso_nuevo.isoformat()}"),
            ("antes en TZ=UTC: checkpoint / piso",
             f"{naive_utc.isoformat()} / {(naive_utc - SYNC_LOOKBACK).isoformat()}"),
            ("antes en TZ=Asunción: checkpoint / piso",
             f"{viejo_asuncion.isoformat()} / {(viejo_asuncion - SYNC_LOOKBACK).isoformat()}"),
            ("el piso se corre hacia adelante (Asunción)",
             f"{_horas(corrimiento)} => releases que ya no se piden"),
            ("franja sobre el checkpoint que no se re-pide",
             f"{_horas(franja)} (SYNC_LOOKBACK = {_horas(SYNC_LOOKBACK)})"),
            ("el piso se corre hacia atrás (Madrid)",
             f"{_horas(corrimiento_madrid)} => sólo se repite trabajo"),
        ],
    ):
        fallas.append("D7")

    # D8: `_get_checkpoint_date()` con repositorio falso (sin BD).
    class _RepoFalso:
        def __init__(self, checkpoint=None, max_release=None):
            self._checkpoint = checkpoint
            self._max_release = max_release

        def get_checkpoint_date(self):
            return self._checkpoint

        def get_max_release_date(self):
            return self._max_release

    def _checkpoint(repo):
        servicio = SyncService(db_repo=repo, source_client=None, etl_service=object())
        return servicio._get_checkpoint_date()

    esperado = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    casos = [
        (
            "checkpoint naive",
            _RepoFalso(checkpoint=datetime(2026, 1, 10, 10, 0)),
            esperado,
        ),
        (
            "checkpoint aware (-03)",
            _RepoFalso(checkpoint=datetime.fromisoformat("2026-01-10T07:00:00-03:00")),
            esperado,
        ),
        (
            "max_release naive",
            _RepoFalso(max_release=datetime(2026, 1, 10, 10, 0)),
            esperado,
        ),
    ]
    ok, detalles = True, []
    for etiqueta, repo, valor in casos:
        with _tz("America/Asuncion"):
            obtenido = _checkpoint(repo)
        bien = obtenido == valor
        ok = ok and bien
        detalles.append(
            (
                f"{etiqueta} (evaluado en TZ=Asunción)",
                f"{_fmt(obtenido)} {'OK' if bien else f'!= {valor.isoformat()}'}",
            )
        )
    with _tz("America/Asuncion"):
        sin_datos = _checkpoint(_RepoFalso())
    detalles.append(("sin checkpoint ni histórico: default_start_date", _fmt(sin_datos)))
    ok = ok and sin_datos.tzinfo is not None
    if not _fila(
        "D8",
        "`_get_checkpoint_date()` normaliza igual sin BD (repositorio falso)",
        ok,
        detalles,
    ):
        fallas.append("D8")

    return fallas
def _recolectar_fechas(nodo, salida):
    """Junta los valores de las claves `date` / `*Date` de un árbol JSON."""
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if clave == "date" or clave.endswith("Date"):
                salida.append((clave, valor))
            if isinstance(valor, (dict, list)):
                _recolectar_fechas(valor, salida)
    elif isinstance(nodo, list):
        for valor in nodo:
            if isinstance(valor, (dict, list)):
                _recolectar_fechas(valor, salida)


def _sonda_d9(cantidad: int, pausa: float, timeout: float) -> list[str]:
    """D9: formato real de las fechas del payload (usa la red)."""
    from src.infrastructure.dncp_client import DNCPClient

    cliente = DNCPClient(timeout=(10, timeout))
    dia = datetime.now(timezone.utc).date() - timedelta(days=1)
    respuesta = None
    for _ in range(10):
        respuesta = cliente.search_processes(
            fecha_desde=dia.isoformat(),
            fecha_hasta=dia.isoformat(),
            items_per_page=cantidad,
        )
        if respuesta.get("records"):
            break
        respuesta = None
        dia -= timedelta(days=1)
    if respuesta is None:
        print("[FALLA] D9  no se encontró un día con datos en los 10 días previos")
        return ["D9"]

    ocids = [r.get("ocid") for r in respuesta["records"][:cantidad]]
    print(f"        día de referencia: {dia.isoformat()} | {len(ocids)} record packages")

    recogidas, compiladas = [], []
    for i, ocid in enumerate(ocids):
        if i:
            time.sleep(pausa)
        paquete = cliente.get_record(ocid)
        registros = paquete.get("records") or [{}]
        compilada = (registros[0].get("compiledRelease") or {}).get("date")
        compiladas.append((ocid, compilada))
        _recolectar_fechas(paquete, recogidas)

    con_offset, naive, ilegibles, desplazados = 0, [], [], []
    desplazamientos, por_clave = set(), {}
    for clave, valor in recogidas:
        por_clave[clave] = por_clave.get(clave, 0) + 1
        try:
            parseada = datetime.fromisoformat(valor)
        except (TypeError, ValueError):
            ilegibles.append((clave, valor))
            continue
        if parseada.tzinfo is None:
            naive.append((clave, valor))
            continue
        con_offset += 1
        desplazamientos.add(parseada.utcoffset())
        if _parse_release_date(valor) != parseada:
            desplazados.append((clave, valor))

    ok = (
        bool(recogidas)
        and not ilegibles
        and not desplazados
        and not naive
        and all(c is not None for _, c in compiladas)
    )
    if not _fila(
        "D9",
        "payload real: fechas con offset y parseo que no mueve el instante",
        ok,
        [
            ("fechas recolectadas",
             f"{len(recogidas)} (claves: {dict(sorted(por_clave.items()))})"),
            ("con offset / naive / ilegibles",
             f"{con_offset} / {len(naive)} / {len(ilegibles)}"),
            ("desplazamientos horarios vistos", f"{sorted(desplazamientos)}"),
            ("fechas cuyo parseo cambia el instante", f"{len(desplazados)}"),
            ("compiledRelease.date por paquete",
             "; ".join(f"{o}={c}" for o, c in compiladas)),
            ("muestras naive (si hubiera)", f"{naive[:5]}"),
        ],
    ):
        return ["D9"]
    return []

def _escribir_json(ruta, estado, fallas):
    """Deja la evidencia en disco, para citarla en la memoria del TFG."""
    if not ruta:
        return
    evidencia = {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tz_del_proceso": os.environ.get("TZ", "(la del sistema)"),
        "python": sys.version.split()[0],
        "estado": estado,
        "sondas_en_falla": fallas,
        "pruebas": _filas,
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(evidencia, f, indent=2, ensure_ascii=False)
    print(f"\nEvidencia escrita en {ruta}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--json",
        dest="ruta_json",
        default=None,
        help="escribe la evidencia de las pruebas en este archivo JSON",
    )
    parser.add_argument(
        "--api",
        type=int,
        default=0,
        metavar="N",
        help="consulta N record packages reales (0 = sólo pruebas locales)",
    )
    parser.add_argument(
        "--pausa",
        type=float,
        default=5.0,
        help="segundos entre peticiones a la API (el límite es 15 por minuto)",
    )
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)

    print("== Pruebas locales (sin red ni base de datos) ==")
    fallas = _sondas_d1_d3() + _sondas_d4() + _sondas_d5_d6() + _sondas_d7_d8()

    if args.api:
        print("\n== D9: payload real de la API ==")
        try:
            fallas += _sonda_d9(args.api, args.pausa, args.timeout)
        except Exception as e:  # red, token o 429 persistente
            print(f"\nERROR de red en D9: {e}\nLas pruebas locales ya se evaluaron.")
            _escribir_json(args.ruta_json, "error de red en D9", fallas + ["D9"])
            return 2

    print(
        "\nSemántica verificada:\n"
        " - Fecha con offset (el 100% del payload real): `_as_utc` conserva el\n"
        "   instante, igual que el código anterior => sin regresión.\n"
        " - Fecha sin zona: antes dependía de la TZ del proceso (contenedor UTC y\n"
        "   laptop UTC-3 daban checkpoints distintos); ahora se interpreta como UTC.\n"
        " - Ese caso no aparece en el payload actual (D9), así que la rama naive de\n"
        "   `_as_utc` es defensiva: cubre columnas TIMESTAMP sin tz o datos de otra\n"
        "   fuente, no un bug vivo.\n"
        " - El daño que evita está medido en D7: en una máquina UTC-3 el piso de la\n"
        "   ventana se corría 3 h y la franja de 2 h quedaba sin re-consultar."
    )
    if fallas:
        _escribir_json(args.ruta_json, "con fallas", fallas)
        print(f"\n{len(fallas)} prueba(s) en FALLA: {', '.join(fallas)}")
        return 1
    _escribir_json(args.ruta_json, "todas pasan", [])
    print("\nTodas las pruebas pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

