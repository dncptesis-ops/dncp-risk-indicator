"""Conjunto de datos de prueba armado a mano, con el formato de los CSV de la DNCP.

Cada proceso prueba un caso concreto. Los resultados esperados de los indicadores
(RESULTADOS_ESPERADOS) se calcularon a mano a partir de estos procesos.

Entidades: A (DNCP-SICP-CODE-1) y B (DNCP-SICP-CODE-2), cada una con una unidad de
contratación (procuringEntity).
"""

import csv
from pathlib import Path

ENTIDAD = {
    "A": ("DNCP-SICP-CODE-1", "Entidad A", "DNCP-SICP-CODE-11", "Unidad A"),
    "B": ("DNCP-SICP-CODE-2", "Entidad B", "DNCP-SICP-CODE-22", "Unidad B"),
}
PROVEEDOR_UNO = ("PY-RUC-80000001-1", "Proveedor Uno SA")
PROVEEDOR_DOS = ("PY-RUC-80000002-2", "Proveedor Dos SRL")
PROVEEDOR_TRES = ("PY-RUC-80000003-3", "Proveedor Tres SA")

# ---------------------------------------------------------------------------
# R018: licitaciones. (ocid, release, fecha del release, entidad, método,
# numberOfTenderers, fin del período de ofertas, oferentes)
# ---------------------------------------------------------------------------
LICITACIONES = [
    # T1: abierta con un solo oferente -> marcada (2024-03)
    ("T1", "T1-r1", "2024-03-10T10:00:00-04:00", "A", "open", "1", "2024-03-05T10:00:00-04:00", [PROVEEDOR_UNO]),
    # T2: abierta con tres oferentes -> evaluada, no marcada (2024-05)
    ("T2", "T2-r1", "2024-05-25T10:00:00-04:00", "A", "open", "3", "2024-05-20T10:00:00-04:00", [PROVEEDOR_UNO, PROVEEDOR_DOS, PROVEEDOR_TRES]),
    # T3: selectiva con un solo oferente -> marcada (2025-02)
    ("T3", "T3-r1", "2025-02-15T10:00:00-04:00", "B", "selective", "1", "2025-02-10T10:00:00-04:00", [PROVEEDOR_UNO]),
    # T4: contratación directa con un oferente -> no se evalúa (no es competitiva)
    ("T4", "T4-r1", "2024-06-05T10:00:00-04:00", "A", "direct", "1", "2024-06-01T10:00:00-04:00", [PROVEEDOR_DOS]),
    # T5: abierta sin número de oferentes -> no se evalúa
    ("T5", "T5-r1", "2024-07-05T10:00:00-04:00", "B", "open", "", "2024-07-01T10:00:00-04:00", []),
    # T6: abierta con un oferente, pero con fecha en el futuro -> no se cuenta
    ("T6", "T6-r1", "2024-12-01T10:00:00-04:00", "A", "open", "1", "2099-01-01T10:00:00-04:00", [PROVEEDOR_DOS]),
    # T7: abierta con un oferente, pero anterior a 2020 -> no se cuenta
    ("T7", "T7-r1", "2019-06-05T10:00:00-04:00", "B", "open", "1", "2019-06-01T10:00:00-04:00", [PROVEEDOR_DOS]),
    # T8: dos versiones del mismo proceso. La vieja tenía 1 oferente y la vigente 2:
    # cuenta una sola vez, con la versión vigente -> evaluada, no marcada (2024-02)
    ("T8", "T8-r1", "2024-01-15T10:00:00-04:00", "B", "open", "1", "2024-01-10T10:00:00-04:00", [PROVEEDOR_TRES]),
    ("T8", "T8-r2", "2024-02-15T10:00:00-04:00", "B", "open", "2", "2024-02-10T10:00:00-04:00", [PROVEEDOR_TRES, PROVEEDOR_DOS]),
]

# ---------------------------------------------------------------------------
# R063 y R064: contratos. (ocid, release, fecha del release, entidad,
# [(contrato, estado, fecha de firma, inicio, documentos, modificaciones)])
# documentos: lista de (id, documentType, título); modificaciones: (id, fecha, descripción)
# ---------------------------------------------------------------------------
FIRMADO = [("doc-f", "contractSigned", "contrato-firmado.pdf")]
PROCESOS_CON_CONTRATOS = [
    # C1: contrato activo con el contrato firmado publicado -> R063 no marcado
    ("C1", "C1-r1", "2024-04-02T10:00:00-04:00", "A", [
        ("C1-k1", "active", "2024-04-01T10:00:00-04:00", "", FIRMADO, []),
    ]),
    # C2: dos contratos activos, uno sin documento -> R063 marcado, una sola vez
    ("C2", "C2-r1", "2024-06-15T10:00:00-04:00", "A", [
        ("C2-k1", "active", "2024-06-10T10:00:00-04:00", "", FIRMADO, []),
        ("C2-k2", "active", "2024-06-12T10:00:00-04:00", "", [], []),
    ]),
    # C3: contrato activo sin documentos -> R063 marcado (2025-03)
    ("C3", "C3-r1", "2025-03-02T10:00:00-04:00", "B", [
        ("C3-k1", "active", "2025-03-01T10:00:00-04:00", "", [], []),
    ]),
    # C4: contrato cancelado sin documentos -> no se evalúa en R063 ni en R064
    ("C4", "C4-r1", "2024-08-02T10:00:00-04:00", "B", [
        ("C4-k1", "cancelled", "2024-08-01T10:00:00-04:00", "", [], []),
    ]),
    # C5: el contrato se subió con otro tipo de documento -> R063 marcado
    ("C5", "C5-r1", "2024-09-02T10:00:00-04:00", "A", [
        ("C5-k1", "active", "2024-09-01T10:00:00-04:00", "", [("doc-n", "", "contrato.pdf")], []),
    ]),
    # C6: contrato activo sin documentos, firmado en el futuro -> no se cuenta
    ("C6", "C6-r1", "2024-10-02T10:00:00-04:00", "B", [
        ("C6-k1", "active", "2099-05-01T10:00:00-04:00", "", [], []),
    ]),
    # C7: sin fecha de firma, se usa el inicio del contrato -> R063 no marcado (2024-10)
    ("C7", "C7-r1", "2024-10-05T10:00:00-04:00", "B", [
        ("C7-k1", "active", "", "2024-10-01T10:00:00-04:00", FIRMADO, []),
    ]),
    # M1: activo con una modificación -> R064 marcado (2024-02)
    ("M1", "M1-r1", "2024-05-02T10:00:00-04:00", "A", [
        ("M1-k1", "active", "2024-02-01T10:00:00-04:00", "", FIRMADO, [("M1-a1", "2024-05-01T00:00:00-04:00", "Ampliación de Plazo")]),
    ]),
    # M2: terminado con una rescisión -> R064 marcado (2024-03)
    ("M2", "M2-r1", "2024-07-02T10:00:00-04:00", "B", [
        ("M2-k1", "terminated", "2024-03-01T10:00:00-04:00", "", FIRMADO, [("M2-a1", "2024-07-01T00:00:00-04:00", "Rescisión")]),
    ]),
    # M3: activo sin modificaciones -> R064 no marcado (2025-01)
    ("M3", "M3-r1", "2025-01-16T10:00:00-04:00", "A", [
        ("M3-k1", "active", "2025-01-15T10:00:00-04:00", "", FIRMADO, []),
    ]),
    # M4: cancelado con una modificación -> no se evalúa en R064
    ("M4", "M4-r1", "2024-04-06T10:00:00-04:00", "B", [
        ("M4-k1", "cancelled", "2024-04-01T10:00:00-04:00", "", FIRMADO, [("M4-a1", "2024-04-05T00:00:00-04:00", "Ampliación de Monto")]),
    ]),
    # M5: dos contratos activos con modificaciones (2 y 1) -> R064 marcado una sola vez
    ("M5", "M5-r1", "2024-09-20T10:00:00-04:00", "A", [
        ("M5-k1", "active", "2024-08-01T10:00:00-04:00", "", FIRMADO, [
            ("M5-a1", "2024-09-01T00:00:00-04:00", "Ampliación de Monto"),
            ("M5-a2", "2024-09-15T00:00:00-04:00", "Ampliación de Plazo"),
        ]),
        ("M5-k2", "active", "2024-08-05T10:00:00-04:00", "", FIRMADO, [("M5-a3", "2024-09-10T00:00:00-04:00", "Prórrogas")]),
    ]),
    # M6: activo con una modificación, pero firmado antes de 2020 -> no se cuenta
    ("M6", "M6-r1", "2019-12-05T10:00:00-04:00", "B", [
        ("M6-k1", "active", "2019-12-01T10:00:00-04:00", "", FIRMADO, [("M6-a1", "2019-12-20T00:00:00-04:00", "Ampliación de Plazo")]),
    ]),
]

# Calculado a mano a partir de los procesos de arriba.
RESULTADOS_ESPERADOS = {
    # R018 evalúa T1, T2, T3 y T8; marca T1 y T3.
    "r018": {"total": 4, "marcados": 2, "porcentaje": 50.0},
    "r018_2024": {"total": 3, "marcados": 1, "porcentaje": 33.3},
    "r018_2025": {"total": 1, "marcados": 1, "porcentaje": 100.0},
    "r018_selective": {"total": 1, "marcados": 1, "porcentaje": 100.0},
    "r018_meses": [("2024-02", 1, 0), ("2024-03", 1, 1), ("2024-05", 1, 0), ("2025-02", 1, 1)],
    # R063 evalúa todo proceso con contratos activos: C1, C2, C3, C5, C7, M1, M3 y M5;
    # marca C2, C3 y C5.
    "r063": {"total": 8, "marcados": 3, "porcentaje": 37.5},
    "r063_2024": {"total": 6, "marcados": 2, "porcentaje": 33.3},
    "r063_2025": {"total": 2, "marcados": 1, "porcentaje": 50.0},
    "r063_entidad_A": {"total": 6, "marcados": 2, "porcentaje": 33.3},
    "r063_entidad_B": {"total": 2, "marcados": 1, "porcentaje": 50.0},
    # R064 evalúa todo proceso con contratos activos o terminados: C1, C2, C3, C5, C7,
    # M1, M2, M3 y M5; marca M1, M2 y M5.
    "r064": {"total": 9, "marcados": 3, "porcentaje": 33.3},
    "r064_2024": {"total": 7, "marcados": 3, "porcentaje": 42.9},
    "r064_2025": {"total": 2, "marcados": 0, "porcentaje": 0.0},
    "r064_entidad_A": {"total": 6, "marcados": 2, "porcentaje": 33.3},
    "r064_entidad_B": {"total": 3, "marcados": 1, "porcentaje": 33.3},
}


def _escribir(ruta: Path, filas: list[dict]) -> None:
    columnas = list(dict.fromkeys(k for fila in filas for k in fila))
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)


def _partes(release: str, entidad: str) -> list[dict]:
    buyer_id, buyer, unidad_id, unidad = ENTIDAD[entidad]
    return [
        {"compiledRelease/id": release, "compiledRelease/parties/0/id": buyer_id,
         "compiledRelease/parties/0/name": buyer, "compiledRelease/parties/0/roles": "buyer"},
        {"compiledRelease/id": release, "compiledRelease/parties/0/id": unidad_id,
         "compiledRelease/parties/0/name": unidad, "compiledRelease/parties/0/roles": "procuringEntity"},
    ]


def escribir_csvs(carpeta: Path) -> None:
    """Escribe los CSV en `carpeta` con los nombres y columnas que usa la DNCP."""
    records, parties, tenderers, contracts, documentos, modificaciones = [], [], [], [], [], []

    for ocid, release, fecha, entidad, metodo, n, fin, oferentes in LICITACIONES:
        records.append({
            "compiledRelease/id": release, "compiledRelease/ocid": f"ocds-prueba-{ocid}",
            "compiledRelease/date": fecha, "compiledRelease/tender/id": ocid,
            "compiledRelease/tender/title": f"Licitación {ocid}",
            "compiledRelease/tender/procurementMethod": metodo,
            "compiledRelease/tender/numberOfTenderers": n,
            "compiledRelease/tender/tenderPeriod/endDate": fin,
        })
        parties += _partes(release, entidad)
        tenderers += [{"compiledRelease/id": release, "compiledRelease/tender/tenderers/0/id": pid,
                       "compiledRelease/tender/tenderers/0/name": nombre} for pid, nombre in oferentes]

    for ocid, release, fecha, entidad, lista in PROCESOS_CON_CONTRATOS:
        records.append({
            "compiledRelease/id": release, "compiledRelease/ocid": f"ocds-prueba-{ocid}",
            "compiledRelease/date": fecha, "compiledRelease/tender/id": ocid,
            "compiledRelease/tender/title": f"Proceso {ocid}",
        })
        parties += _partes(release, entidad)
        for contrato, estado, firma, inicio, docs, mods in lista:
            contracts.append({
                "compiledRelease/id": release, "compiledRelease/contracts/0/id": contrato,
                "compiledRelease/contracts/0/awardID": f"award-{contrato}",
                "compiledRelease/contracts/0/status": estado,
                "compiledRelease/contracts/0/dateSigned": firma,
                "compiledRelease/contracts/0/period/startDate": inicio,
            })
            documentos += [{
                "compiledRelease/id": release, "compiledRelease/contracts/0/id": contrato,
                "compiledRelease/contracts/0/documents/0/id": f"{contrato}-{doc}",
                "compiledRelease/contracts/0/documents/0/documentType": tipo,
                "compiledRelease/contracts/0/documents/0/title": titulo,
            } for doc, tipo, titulo in docs]
            modificaciones += [{
                "compiledRelease/id": release, "compiledRelease/contracts/0/id": contrato,
                "compiledRelease/contracts/0/amendments/0/id": mid,
                "compiledRelease/contracts/0/amendments/0/date": mfecha,
                "compiledRelease/contracts/0/amendments/0/description": desc,
            } for mid, mfecha, desc in mods]

    _escribir(carpeta / "records.csv", records)
    _escribir(carpeta / "parties.csv", parties)
    _escribir(carpeta / "ten_tenderers.csv", tenderers)
    _escribir(carpeta / "contracts.csv", contracts)
    _escribir(carpeta / "con_documents.csv", documentos)
    _escribir(carpeta / "con_amendments.csv", modificaciones)
