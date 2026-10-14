"""
Pruebas contra la API real de /search/processes de la DNCP.

La documentación oficial no dice cómo interpreta fecha_desde / fecha_hasta, ni el
límite de resultados o de peticiones, así que este script lo verifica (P1 a P22).
El resumen de lo medido está en docs/api_dncp_fechas_y_limites.md.

Uso (desde backend/):

    python -m src.scripts.v2.probar_ventana_fechas
    python -m src.scripts.v2.probar_ventana_fechas --dia 2026-09-07
    python -m src.scripts.v2.probar_ventana_fechas --pausa 6 --timeout 90

Sale con 1 si alguna prueba falla y con 2 si falla la red. Espera 5 s entre
peticiones porque la API permite 15 por minuto.
"""

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

import requests

API_URL_POR_DEFECTO = (
    "https://www.contrataciones.gov.py/datos/api/v3/doc/search/processes"
)
TZ_POR_DEFECTO = "America/Asuncion"
PAUSA_POR_DEFECTO = 5.0  # el anuncio de la API es 15 peticiones/minuto
DIA_ATRAS_POR_DEFECTO = 7
DIAS_BUSCANDO_DATOS = 14
REINTENTOS_429 = 2  # la API responde 429 pasajeros al agotar la cuota
ESPERA_429_MAX = 60.0  # techo de la espera aunque Retry-After pida más

# Piso de la ventana probado a mano: hora local (UTC-3) de un release del CSV.
CASO_DESDE_LOCAL = "2026-08-25T14:58:00-03:00"  # == 17:58:00Z
CASO_DESDE_UTC = "2026-08-25T17:58:00Z"
CASO_DESDE_UTC_MAL = "2026-08-25T14:58:00Z"  # como si el offset se ignorara
CASO_HASTA = "2026-08-26T00:00:00Z"
CASO_HASTA_INVERTIDA = "2026-08-25T17:00:00Z"  # sólo invierte si se honra -03
SIN_DATOS_DESDE = "2099-01-01"
SIN_DATOS_HASTA = "2099-01-02"

_ultima_llamada = 0.0


class Respuesta(NamedTuple):
    """Resultado de una consulta: interesa el conteo, el piso real y el cuerpo."""

    status: int
    total: int | None  # pagination.total_items
    primera_fecha: str | None  # compiledRelease.date del primer item (order asc)
    cuerpo: str = ""  # mensaje de la API cuando no es 200 (cortado)
    bytes: int = 0  # tamaño de la respuesta (para dimensionar la memoria)

    @property
    def vacia(self) -> bool:
        """La API responde 404 cuando la ventana no tiene registros."""
        return self.status == 404


def _esperar_turno(pausa: float) -> None:
    """Espacia las peticiones para no chocar con el límite de 15/minuto."""
    global _ultima_llamada
    espera = pausa - (time.monotonic() - _ultima_llamada)
    if espera > 0:
        time.sleep(espera)
    _ultima_llamada = time.monotonic()


def _get(api_url: str, params: dict, timeout: float, headers: dict | None = None):
    """GET que reintenta con espera ante un 429 pasajero.

    El 429 de esta API es transitorio (el mismo contador que anuncia 15/min deja
    pasar ráfagas y se recupera en segundos) y su cuerpo es *el mismo* que el de
    un token inválido: `{"message": "Number of request exceeded or invalid
    token"}`. Por eso conviene esperar el `Retry-After` y reintentar, en vez de
    dar la prueba por fallida: es lo mismo que hace el cliente real.
    """
    global _ultima_llamada
    for intento in range(REINTENTOS_429 + 1):
        resp = requests.get(api_url, params=params, headers=headers, timeout=timeout)
        if resp.status_code != 429 or intento == REINTENTOS_429:
            return resp
        try:
            espera = float(resp.headers.get("Retry-After") or 0)
        except (TypeError, ValueError):
            espera = 0.0
        espera = min(max(espera, PAUSA_POR_DEFECTO), ESPERA_429_MAX)
        print(f"        429 pasajero: reintento en {espera:.0f}s (límite de la API)")
        time.sleep(espera)
        _ultima_llamada = time.monotonic()


def consultar(params: dict, api_url: str, pausa: float, timeout: float) -> Respuesta:
    """GET /search/processes. Con 1 item basta: sólo se comparan conteos."""
    _esperar_turno(pausa)
    query = {
        "tipo_fecha": "fecha_release",
        "page": 1,
        "items_per_page": 1,  # el total_items no depende del tamaño de página
        "order": "date asc",  # el primer item es la fecha mínima devuelta
    }
    query.update(params)
    resp = _get(api_url, query, timeout)
    if resp.status_code != 200:
        return Respuesta(resp.status_code, None, None, resp.text[:200])
    cuerpo = resp.json()
    registros = cuerpo.get("records") or []
    return Respuesta(
        resp.status_code,
        (cuerpo.get("pagination") or {}).get("total_items"),
        (registros[0].get("compiledRelease") or {}).get("date") if registros else None,
        "",
        len(resp.content),
    )


def pedir_crudo(params: dict, api_url: str, pausa: float, timeout: float):
    """GET sin transformar: para las pruebas que necesitan el cuerpo completo."""
    _esperar_turno(pausa)
    query = {
        "tipo_fecha": "fecha_release",
        "page": 1,
        "items_per_page": 1,
        "order": "date asc",
    }
    query.update(params)
    return _get(api_url, query, timeout)


def _token_del_env() -> str | None:
    """Lee `DNCP_REQUEST_TOKEN` del entorno o del `.env`, si existe.

    El script no importa `src.config` a propósito: verifica la API pública, no la
    aplicación, y así corre aunque cambie la configuración del proyecto.
    """
    valor = os.environ.get("DNCP_REQUEST_TOKEN")
    if valor:
        return valor.strip()
    for ruta in (Path(".env"), Path(__file__).resolve().parents[3] / ".env"):
        try:
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                if linea.strip().startswith("DNCP_REQUEST_TOKEN"):
                    return linea.partition("=")[2].strip().strip("'\"") or None
        except OSError:
            continue
    return None



def _dia_con_datos(
    dia: date, api_url: str, pausa: float, timeout: float
) -> tuple[str, Respuesta]:
    """Primer día hacia atrás con registros (un domingo, por ejemplo, no tiene)."""
    for _ in range(DIAS_BUSCANDO_DATOS):
        iso = dia.isoformat()
        r = consultar(
            {"fecha_desde": iso, "fecha_hasta": iso}, api_url, pausa, timeout
        )
        if r.total:
            return iso, r
        dia -= timedelta(days=1)
    raise SystemExit(
        f"No se encontró un día con datos en los {DIAS_BUSCANDO_DATOS} días previos."
    )


def _sondear(args) -> list[str]:
    """Corre las pruebas, imprime la tabla y devuelve la lista de fallas."""
    api_url, pausa, timeout = args.api_url, args.pausa, args.timeout
    hoy_local = datetime.now(timezone.utc).astimezone(ZoneInfo(args.tz)).date()
    dia_inicial = (
        date.fromisoformat(args.dia)
        if args.dia
        else hoy_local - timedelta(days=args.dias_atras)
    )
    fallas: list[str] = []

    def fila(prueba, verificacion, ok, respuestas=()):
        print(f"[{'OK' if ok else 'FALLA'}] {prueba:<3} {verificacion}")
        for etiqueta, r in respuestas:
            estado = "404 (sin registros)" if r.vacia else str(r.status)
            total = "-" if r.total is None else str(r.total)
            minimo = r.primera_fecha or "-"
            print(
                f"        {etiqueta:<44} -> HTTP {estado:<18} "
                f"total={total:<7} min={minimo}"
            )
            if r.cuerpo:
                print(f"            cuerpo: {r.cuerpo}")
        if not ok:
            fallas.append(f"{prueba} ({verificacion})")

    def nota(etiqueta, texto):
        """Línea de detalle para las pruebas que no son igualdades de ventanas."""
        print(f"        {etiqueta:<44} -> {texto}")


    def pedir(**params):
        return consultar(params, api_url, pausa, timeout)

    print(
        "\nFecha UTC de la ejecución: "
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    )
    print(f"API: {api_url}\n")

    dia, base = _dia_con_datos(dia_inicial, api_url, pausa, timeout)
    print(f"Día de referencia con datos: {dia} (total_items={base.total})")
    print(
        "Ventanas de un solo día: quedan lejos del techo de 10.000 items por\n"
        "listado (P11 lo mide), así que los conteos son comparables.\n"
    )

    desde_dia = date.fromisoformat(dia)
    siguiente_utc = f"{desde_dia + timedelta(days=1)}T00:00:00Z"
    techo_local_offset = f"{desde_dia + timedelta(days=1)}T00:00:00-03:00"
    techo_local_utc = f"{desde_dia + timedelta(days=1)}T03:00:00Z"

    # P1: un día suelto va de 00:00Z de D a 00:00Z de D+1.
    piso_utc = f"{dia}T00:00:00Z"
    r1a = pedir(fecha_desde=piso_utc, fecha_hasta=siguiente_utc)
    fila(
        "P1a",
        "día suelto (desde=D hasta=D) == [D 00:00Z, D+1 00:00Z]",
        base.status == 200
        and r1a.status == 200
        and base.total == r1a.total
        and base.primera_fecha == r1a.primera_fecha,
        [(f"desde={dia} hasta={dia} (sueltos)", base), (f"desde={piso_utc} hasta={siguiente_utc}", r1a)],
    )

    # P1b: el piso es 00:00Z, no la medianoche local.
    r1b = pedir(fecha_desde=dia, fecha_hasta=siguiente_utc)
    fila(
        "P1b",
        "desde=<día suelto> == desde=00:00Z del mismo día",
        base.status == 200
        and r1b.status == 200
        and r1b.total == r1a.total
        and r1b.primera_fecha == r1a.primera_fecha,
        [(f"desde={dia} hasta={siguiente_utc}", r1b), (f"desde={piso_utc} hasta={siguiente_utc}", r1a)],
    )

    # P1c: si el techo fuera 00:00Z del mismo día, el día suelto vendría vacío.
    r1c = pedir(fecha_desde=dia, fecha_hasta=piso_utc)
    fila(
        "P1c",
        "desde=D hasta=D 00:00Z => 404 (el techo suelto NO es el 00:00Z de D)",
        (base.total or 0) > 0 and (r1c.vacia or (r1c.total or 0) == 0),
        [(f"desde={dia} hasta={piso_utc}", r1c), (f"desde={dia} hasta={dia} (contraste)", base)],
    )

    # P2: en el techo el offset del string se respeta.
    r2a = pedir(fecha_desde=dia, fecha_hasta=techo_local_offset)
    r2b = pedir(fecha_desde=dia, fecha_hasta=techo_local_utc)
    fila(
        "P2",
        "hasta=00:00-03:00 == hasta=03:00Z (offset honrado en el techo)",
        r2a.status == 200 and r2a.total == r2b.total,
        [(f"hasta={techo_local_offset}", r2a), (f"hasta={techo_local_utc}", r2b)],
    )

    # P3: el mismo instante con offset y en UTC da el mismo conjunto.
    r3a = pedir(fecha_desde=CASO_DESDE_LOCAL, fecha_hasta=CASO_HASTA)
    r3b = pedir(fecha_desde=CASO_DESDE_UTC, fecha_hasta=CASO_HASTA)
    fila(
        "P3",
        "desde=14:58:00-03:00 == desde=17:58:00Z (offset honrado en el piso)",
        r3a.status == 200 and r3a.total == r3b.total,
        [(f"desde={CASO_DESDE_LOCAL}", r3a), (f"desde={CASO_DESDE_UTC}", r3b)],
    )

    # P4: interpretar esa hora como UTC incluiría la franja anterior.
    r4 = pedir(fecha_desde=CASO_DESDE_UTC_MAL, fecha_hasta=CASO_HASTA)
    fila(
        "P4",
        "desde=14:58:00Z trae la franja anterior (>= P3: el offset no se ignora)",
        r4.status == 200 and r4.total is not None and r4.total >= r3b.total,
        [(f"desde={CASO_DESDE_UTC_MAL}", r4)],
    )

    # P5: ventana invertida -> 404 (no un 200 con lista vacía).
    r5 = pedir(fecha_desde=CASO_DESDE_LOCAL, fecha_hasta=CASO_HASTA_INVERTIDA)
    fila(
        "P5",
        "ventana invertida (17:58Z > 17:00Z) => HTTP 404",
        r5.vacia,
        [(f"desde={CASO_DESDE_LOCAL} hasta={CASO_HASTA_INVERTIDA}", r5)],
    )

    # P6: inclusivos y por instante: el registro exacto se devuelve.
    instante = base.primera_fecha
    r6 = pedir(fecha_desde=instante, fecha_hasta=instante)
    fila(
        "P6",
        "desde = hasta = <instante real> devuelve ese registro (inclusivo)",
        r6.status == 200 and (r6.total or 0) >= 1 and r6.primera_fecha == instante,
        [(f"desde=hasta={instante}", r6)],
    )

    # P7: mezcla de formatos (piso con hora y offset + techo como día suelto).
    r7 = pedir(fecha_desde=instante, fecha_hasta=dia)
    fila(
        "P7",
        "piso con hora/offset + techo como día suelto: devuelve registros",
        r7.status == 200 and (r7.total or 0) >= 1,
        [(f"desde={instante} hasta={dia}", r7)],
    )

    # P8: rango sin datos -> 404.
    r8 = pedir(fecha_desde=SIN_DATOS_DESDE, fecha_hasta=SIN_DATOS_HASTA)
    fila(
        "P8",
        "rango sin datos (año futuro) => HTTP 404",
        r8.vacia,
        [(f"desde={SIN_DATOS_DESDE} hasta={SIN_DATOS_HASTA}", r8)],
    )

    # Pruebas del filtro, del listado y del trato de errores.
    # P9: el filtro usa la última release del proceso.
    crudo = pedir_crudo({"fecha_desde": dia, "fecha_hasta": dia}, api_url, pausa, timeout)
    item = ((crudo.json().get("records") or [{}])[0]) if crudo.status_code == 200 else {}
    releases = [r.get("date") for r in (item.get("releases") or []) if r.get("date")]
    compilada = (item.get("compiledRelease") or {}).get("date")
    if releases and compilada and min(releases, key=datetime.fromisoformat) != compilada:
        vieja = datetime.fromisoformat(
            min(releases, key=datetime.fromisoformat)
        ).isoformat(timespec="seconds")
        hasta_vieja = (
            datetime.fromisoformat(vieja) + timedelta(seconds=1)
        ).isoformat(timespec="seconds")
        r9 = pedir(fecha_desde=vieja, fecha_hasta=hasta_vieja)
        nota(
            "proceso de referencia",
            f"{item.get('ocid')} | {len(releases)} releases | compiled={compilada}",
        )
        nota("release más vieja de ese proceso", vieja)
        fila(
            "P9",
            "ventana de 1 s sobre una release vieja del proceso => 404",
            r9.vacia,
            [(f"desde={vieja} hasta={hasta_vieja}", r9)],
        )
    else:
        print("[OMITIDA] P9  el día no tiene un proceso con release vieja != compiled")

    # P10: el checkpoint se apoya en que compiledRelease.date sea el máximo.
    n_items = 5
    crudo10 = pedir_crudo(
        {"fecha_desde": dia, "fecha_hasta": dia, "items_per_page": n_items},
        api_url,
        pausa,
        timeout,
    )
    items = (crudo10.json().get("records") or []) if crudo10.status_code == 200 else []
    malos, resumen_items = [], []
    for it in items:
        rels = [r.get("date") for r in (it.get("releases") or []) if r.get("date")]
        comp = (it.get("compiledRelease") or {}).get("date")
        if (
            not rels
            or not comp
            or datetime.fromisoformat(comp)
            != max(datetime.fromisoformat(r) for r in rels)
        ):
            malos.append(it.get("ocid"))
        resumen_items.append(f"{it.get('ocid')} ({len(rels)} rel)")
    fila(
        "P10",
        f"compiledRelease.date == max(releases[].date) en {len(items)} items del día",
        bool(items) and not malos,
        [],
    )
    nota("items revisados", ", ".join(resumen_items))
    nota("bytes de la respuesta", f"{len(crudo10.content)} con items_per_page={n_items}")

    # P11: el listado se corta en 10.000 items sin avisar (HTTP 200).
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    r11 = pedir(fecha_desde="2020-01-01", fecha_hasta=ahora, items_per_page=100)
    fila(
        "P11",
        "ventana enorme: total_items=10000 y HTTP 200 (techo silencioso)",
        r11.status == 200 and r11.total == 10000,
        [(f"desde=2020-01-01 hasta=ahora (items_per_page=100)", r11)],
    )
    nota("bytes de esa página", f"{r11.bytes} (lo que baja el sync en una página)")

    # P12: la última página válida da 200 y la siguiente 404. La página sale del
    # total del día, no de un número fijo.
    ultima = base.total or 1
    r12a = pedir(fecha_desde=dia, fecha_hasta=dia, page=ultima)
    r12b = pedir(fecha_desde=dia, fecha_hasta=dia, page=ultima + 1)
    fila(
        "P12",
        "última página del día => 200 y una más allá => 404 "
        "(el cliente traduce el 404 a records=[])",
        r12a.status == 200 and r12b.vacia,
        [
            (f"page={ultima} (última del día de referencia)", r12a),
            (f"page={ultima + 1} (una más allá)", r12b),
        ],
    )

    # P13: order=date desc devuelve primero el máximo del día.
    r13 = pedir(fecha_desde=dia, fecha_hasta=dia, order="date desc")
    maximos = [
        datetime.fromisoformat(it["compiledRelease"]["date"])
        for it in items
        if (it.get("compiledRelease") or {}).get("date")
    ]
    ok13 = (
        r13.status == 200
        and r13.total == base.total
        and r13.primera_fecha is not None
        and (not maximos or datetime.fromisoformat(r13.primera_fecha) >= max(maximos))
    )
    fila(
        "P13",
        "order=date desc: mismo total y el primero es el máximo del día",
        ok13,
        [
            ("order=date desc (items_per_page=1)", r13),
            ("order=date asc (día suelto)", base),
        ],
    )

    # P14: valores admitidos de tipo_fecha.
    r14 = pedir(fecha_desde=dia, fecha_hasta=dia, tipo_fecha="xyz")
    fila(
        "P14",
        "tipo_fecha inválido => 400 con la lista de valores admitidos",
        r14.status == 400 and "fecha_release" in r14.cuerpo,
        [("tipo_fecha=xyz", r14)],
    )

    # P15: fecha mal formada => 500 (el cliente reintenta y la ejecución falla).
    r15 = pedir(fecha_desde="basura", fecha_hasta=dia)
    fila(
        "P15",
        "fecha mal formada => HTTP 500 (bug del servidor, no 400)",
        r15.status == 500,
        [("fecha_desde=basura", r15)],
    )

    # P16/P17: credenciales y cabeceras de límite.
    _esperar_turno(pausa)
    r16 = _get(
        api_url,
        {
            "tipo_fecha": "fecha_release",
            "page": 1,
            "items_per_page": 1,
            "order": "date asc",
            "fecha_desde": dia,
            "fecha_hasta": dia,
        },
        timeout,
    )
    limite = r16.headers.get("X-RateLimit-Limit")
    reset = r16.headers.get("X-RateLimit-Reset")
    fila(
        "P16",
        "sin cabecera Authorization => HTTP 200 (el token no es obligatorio)",
        r16.status_code == 200,
        [],
    )
    nota(
        "límite sin token",
        f"limit={limite} remaining={r16.headers.get('X-RateLimit-Remaining')}",
    )
    reset_ok, faltan = False, "-"
    if reset:
        try:
            faltan = f"{float(reset) - time.time():.0f}s"
            reset_ok = 0 <= float(reset) - time.time() <= 120
        except (TypeError, ValueError):
            reset_ok, faltan = False, f"no numérico: {reset!r}"
    fila(
        "P17",
        "X-RateLimit-Limit=15 por minuto y X-RateLimit-Reset como marca Unix",
        limite == "15" and reset_ok,
        [],
    )
    nota("X-RateLimit-Reset", f"{reset} (vence en {faltan})")

    # P18: sin fecha_hasta la ventana llega hasta ahora.
    semana = (desde_dia - timedelta(days=7)).isoformat()
    ahora18 = datetime.now(timezone.utc).isoformat(timespec="seconds")
    r18a = pedir(fecha_desde=semana)
    r18b = pedir(fecha_desde=semana, fecha_hasta=ahora18)
    total18 = r18b.total or 0
    desfase18 = abs((r18a.total or 0) - total18)
    fila(
        "P18",
        "sin fecha_hasta == hasta ahora (no 'sólo ese día')",
        r18a.status == 200
        and r18b.status == 200
        and desfase18 <= 2  # puede entrar un release entre las dos llamadas
        and total18 > (base.total or 0),
        [(f"desde={semana} SIN hasta", r18a), (f"desde={semana} hasta=ahora", r18b)],
    )
    nota(
        "piso fijo => conjunto creciente",
        f"{total18} items en 7 días (día suelto={base.total}): sin techo hay que "
        "paginar todo el historial en cada ejecución",
    )

    # P19: el tamaño de página sube (menos peticiones) a cambio de RAM.
    paginas_100 = -(-total18 // 100) if total18 else 0
    paginas_1000 = -(-total18 // 1000) if total18 else 0
    r19 = pedir_crudo(
        {"fecha_desde": semana, "fecha_hasta": ahora18, "items_per_page": 1000},
        api_url,
        pausa,
        timeout,
    )
    cuerpo19 = r19.json() if r19.status_code == 200 else {}
    pag19 = cuerpo19.get("pagination") or {}
    n19 = len(cuerpo19.get("records") or [])
    fila(
        "P19",
        f"items_per_page=1000 aceptado: {paginas_1000} páginas en vez de {paginas_100}",
        r19.status_code == 200
        and pag19.get("items_per_page") == 1000
        and pag19.get("total_items") == total18
        and pag19.get("total_pages") == paginas_1000,
        [],
    )
    nota(
        "coste de la página grande",
        f"{len(r19.content)} bytes para {n19} items "
        f"({len(r19.content) // max(1, n19)} B/item) frente a {r11.bytes} bytes "
        "de una página de 100 items (P11)",
    )

    # P20: el token no sube el límite anunciado y el 15/min no corta de verdad.
    token = _token_del_env()
    params20 = {
        "tipo_fecha": "fecha_release",
        "page": 1,
        "items_per_page": 1,
        "order": "date asc",
        "fecha_desde": dia,
        "fecha_hasta": dia,
    }
    limite_con = None
    if token:
        _esperar_turno(pausa)
        r20 = _get(api_url, params20, timeout, headers={"Authorization": token})
        limite_con = r20.headers.get("X-RateLimit-Limit")
        nota(
            "límite con Authorization (token del .env)",
            f"HTTP {r20.status_code} limit={limite_con} "
            f"remaining={r20.headers.get('X-RateLimit-Remaining')}",
        )
    else:
        nota("token del .env", "no configurado: no se compara con/sin OAUTH")
    fallos_rafaga = 0
    for _ in range(6):
        _esperar_turno(1.2)
        if _get(api_url, params20, timeout).status_code != 200:
            fallos_rafaga += 1
    fila(
        "P20",
        "el token no sube el límite anunciado y la ráfaga de 6 no se corta",
        limite_con in (None, limite) and fallos_rafaga <= 1,
        [],
    )
    nota(
        "ráfaga de 6 peticiones a 1,2 s",
        f"respuestas no-200={fallos_rafaga}: ráfagas cortas pasan, pero la cuota "
        "se agota y entonces la API responde 429 pasajero",
    )

    # P21: un token inválido también responde 200.
    _esperar_turno(pausa)
    r21 = _get(api_url, params20, timeout, headers={"Authorization": "no-soy-un-token"})
    fila(
        "P21",
        "token inválido => 200 (la credencial no se valida en el endpoint)",
        r21.status_code == 200,
        [],
    )
    nota(
        "con token inválido",
        f"HTTP {r21.status_code} limit={r21.headers.get('X-RateLimit-Limit')} "
        "(por eso el cliente nunca recibe el 401 que lo haría renovar)",
    )

    # P22: sin tipo_fecha la API ignora la ventana. Va con _get porque pedir()
    # y consultar() siempre agregan tipo_fecha.
    params22 = {
        "page": 1,
        "items_per_page": 1,
        "order": "date asc",
        "fecha_desde": SIN_DATOS_DESDE,
        "fecha_hasta": SIN_DATOS_HASTA,
    }
    r22a = _get(api_url, {**params22, "tipo_fecha": "fecha_release"}, timeout)
    _esperar_turno(pausa)
    r22b = _get(api_url, params22, timeout)
    total22 = None
    if r22b.status_code == 200:
        total22 = (r22b.json().get("pagination") or {}).get("total_items")
    fila(
        "P22",
        "sin tipo_fecha la API ignora la ventana: 200 con el listado entero",
        r22a.status_code == 404 and r22b.status_code == 200,
        [],
    )
    nota(
        "ventana imposible 2099 con y sin tipo_fecha",
        f"con tipo_fecha=HTTP {r22a.status_code}; sin él=HTTP {r22b.status_code} "
        f"total_items={total22} (el filtro de fechas queda anulado; el cliente "
        "siempre lo manda)",
    )

    return fallas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--api-url", default=API_URL_POR_DEFECTO)
    parser.add_argument("--tz", default=TZ_POR_DEFECTO)
    parser.add_argument("--dia", default=None, help="día de referencia (YYYY-MM-DD)")
    parser.add_argument("--dias-atras", type=int, default=DIA_ATRAS_POR_DEFECTO)
    parser.add_argument("--pausa", type=float, default=PAUSA_POR_DEFECTO)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)

    try:
        fallas = _sondear(args)
    except requests.RequestException as e:
        print(f"\nERROR de red: {e}\nSe cortó la verificación, reintentar luego.")
        return 2

    print(
        "\nSemántica verificada (la que implementan `sync_service` y `dncp_client`):\n"
        " - Cada extremo es un instante *inclusive* y el offset del string se\n"
        "   respeta; un día suelto abarca el día UTC completo (piso 00:00Z de D y\n"
        "   techo 00:00Z de D+1), no la medianoche local.\n"
        " - El filtro compara con la ÚLTIMA release del proceso y el paginado\n"
        "   ordena por esa misma fecha: el checkpoint del sync no puede saltar\n"
        "   por delante de releases que todavía no se bajaron.\n"
        " - Ventana vacía o invertida, página fuera de rango y `tipo_fecha`\n"
        "   inválido => 404/400 (el cliente traduce el 404 a records=[]).\n"
        " - El listado se corta en 10.000 items con HTTP 200 y sin aviso: una\n"
        "   ventana más grande queda truncada, así que un piso fijo \"paginar hasta\n"
        "   el final\" es imposible (lo que sobra no se ve nunca). Hay que trocear\n"
        "   la ventana; para el histórico completo (~92.000 procesos) la DNCP\n"
        "   recomienda los CSV por año.\n"
        " - Por eso el sync NO usa un piso fijo: `fecha_hasta = ahora` congela el\n"
        "   conjunto (si se omite, el techo se mueve mientras se pagina) y el piso\n"
        "   móvil (checkpoint - lookback) hace que una ejecución normal recorra 1\n"
        "   página en vez de todo el historial (P18).\n"
        " - `items_per_page` sube a 1000 (6 páginas en vez de 55 sobre 5.475\n"
        "   procesos) a cambio de más RAM: P19 mide 2,27 MB por página de 1000\n"
        "   items, y una página de 1000 items con procesos de miles de releases\n"
        "   llegó a 18.645.965 B (~18,6 MB, medido aparte).\n"
        " - Credenciales y límite: el token no es obligatorio ni se valida en\n"
        "   estos endpoints (un token inválido también da 200) y no sube el límite\n"
        "   anunciado (15/min); la cuota sí se agota y entonces la API responde un\n"
        "   429 pasajero, que el cliente (y este script) reintenta esperando el\n"
        "   `Retry-After` (P16/P17/P20/P21).\n"
        " - `tipo_fecha` es lo que activa el filtro de fechas: **sin él los dos\n"
        "   extremos de la ventana se ignoran** y la API responde 200 con el\n"
        "   listado entero (10.000). `dncp_client` lo manda siempre (P22)."
    )
    if fallas:
        print(f"\n{len(fallas)} prueba(s) en FALLA: {', '.join(fallas)}")
        return 1
    print("\nTodas las pruebas pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
