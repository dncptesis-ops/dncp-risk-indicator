"""
Cobertura de los campos que pide la guía de OCP para R018, R063 y R064.

Sirve para la hipótesis secundaria del trabajo: qué parte de los campos requeridos
publica la DNCP. Para cada campo muestra sobre cuántos casos se midió y en qué porcentaje
viene informado. Se cuentan solo casos con fecha entre INDICATORS_START_DATE y hoy, en su
versión vigente.

Campos (guía de OCP 2024, pp. 41, 86 y 87):
    R018: tender/procurementMethod, tender/numberOfTenderers
          (o tender/tenderers/id, o bids/details/tenderers/id)
    R063: contracts/status, contracts/documents/documentType = contractSigned
    R064: contracts/status, contracts/amendments/description

Uso (desde backend/; usa la base del .env):

    uv run python -m src.scripts.v2.medir_cobertura_campos
"""

import sys

import psycopg2

from src.config import settings
from src.infrastructure.async_db.sql_common import FECHA_CONTRATO, FECHA_LICITACION

DSN = (
    f"postgresql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    f"?sslmode={settings.db_sslmode}"
)

LICITACIONES = f"""
    SELECT t.* FROM latest_releases r JOIN tender t ON t.release_id = r.release_id
    WHERE {FECHA_LICITACION} >= %(desde)s AND {FECHA_LICITACION} <= NOW()
"""
CONTRATOS = f"""
    SELECT c.* FROM latest_releases r JOIN contracts c ON c.release_id = r.release_id
    WHERE {FECHA_CONTRATO} >= %(desde)s AND {FECHA_CONTRATO} <= NOW()
"""

# (indicador, campo, universo, consulta que devuelve (casos, informados))
MEDICIONES = [
    ("R018", "tender/procurementMethod", "licitaciones",
     f"SELECT count(*), count(procurement_method) FROM ({LICITACIONES}) t"),
    ("R018", "tender/numberOfTenderers", "licitaciones competitivas (open o selective)",
     f"SELECT count(*), count(number_of_tenderers) FROM ({LICITACIONES}) t "
     "WHERE procurement_method IN ('open', 'selective')"),
    ("R018", "tender/tenderers/id (alternativa)", "licitaciones competitivas (open o selective)",
     f"SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM tenderers tr "
     f"WHERE tr.release_id = t.release_id)) FROM ({LICITACIONES}) t "
     "WHERE procurement_method IN ('open', 'selective')"),
    ("R063/R064", "contracts/status", "contratos",
     f"SELECT count(*), count(status) FROM ({CONTRATOS}) c"),
    ("R063", "contracts/documents (algún documento)", "contratos activos",
     f"SELECT count(*), count(*) FILTER (WHERE EXISTS (SELECT 1 FROM contract_documents d "
     f"WHERE d.release_id = c.release_id AND d.contract_id = c.contract_id)) "
     f"FROM ({CONTRATOS}) c WHERE status = 'active'"),
    ("R063", "contracts/documents/documentType", "documentos de contratos activos",
     f"SELECT count(*), count(d.document_type) FROM ({CONTRATOS}) c "
     "JOIN contract_documents d ON d.release_id = c.release_id AND d.contract_id = c.contract_id "
     "WHERE c.status = 'active'"),
    ("R064", "contracts/amendments/description", "modificaciones de contratos",
     f"SELECT count(*), count(a.description) FROM ({CONTRATOS}) c "
     "JOIN contract_amendments a ON a.release_id = c.release_id AND a.contract_id = c.contract_id"),
]


def main() -> int:
    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            print(f"Base: {settings.db_host} / {settings.db_name} | desde {settings.indicators_start_date}\n")
            print(f"{'Indicador':10} {'Campo':40} {'Universo':46} {'Casos':>9} {'Informado':>9}")
            for indicador, campo, universo, sql in MEDICIONES:
                cur.execute(sql, {"desde": settings.indicators_start_date})
                casos, informados = cur.fetchone()
                pct = f"{100 * informados / casos:.1f} %" if casos else "sin casos"
                print(f"{indicador:10} {campo:40} {universo:46} {casos:>9} {pct:>9}")
        print("\nbids/details/tenderers/id no se carga: la DNCP publica ofertas casi solo en "
              "subastas electrónicas (decisiones §10).")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
