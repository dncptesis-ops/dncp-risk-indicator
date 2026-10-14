import pandas as pd
import pytest
from unittest.mock import MagicMock

from src.etl.ocds_flatten_ingest import ETLService


def _parties_df(roles_value):
    return pd.DataFrame(
        {
            "compiledRelease/id": ["rel-1"],
            "compiledRelease/parties/0/id": ["party-1"],
            "compiledRelease/parties/0/name": ["Party One"],
            "compiledRelease/parties/0/roles": [roles_value],
        }
    )


def _upsert_calls_for(db, table):
    return [c for c in db.bulk_upsert.call_args_list if c.args[0] == table]


def test_party_roles_drops_party_without_roles():
    db = MagicMock()
    etl = ETLService(db)
    etl.process_release_dataframes({"parties": _parties_df("")})

    calls = _upsert_calls_for(db, "party_roles")
    # La fila con role vacío se descarta antes del upsert (PK vacía)
    assert len(calls) == 0


def test_party_roles_keeps_valid_roles():
    db = MagicMock()
    etl = ETLService(db)
    etl.process_release_dataframes({"parties": _parties_df("buyer;supplier")})

    calls = _upsert_calls_for(db, "party_roles")
    assert len(calls) == 1
    out = calls[0].args[1]
    assert set(out["role"]) == {"buyer", "supplier"}


def test_contracts_drops_row_with_empty_contract_id():
    db = MagicMock()
    etl = ETLService(db)
    df = pd.DataFrame(
        {
            "compiledRelease/id": ["rel-1", "rel-1"],
            "compiledRelease/contracts/0/id": ["CON-1", ""],  # segunda fila sin id
        }
    )

    etl.process_release_dataframes({"contracts": df})

    calls = _upsert_calls_for(db, "contracts")
    assert len(calls) == 1
    assert list(calls[0].args[1]["contract_id"]) == ["CON-1"]


def test_process_mapping_no_convierte_texto_na_en_nan(tmp_path):
    """'NA'/'NULL' son texto válido de un CSV histórico, no valores ausentes.

    Sin keep_default_na=False pandas los vuelve NaN y el dato se pierde
    (p. ej. el nombre de una empresa llamada "NA").
    """
    (tmp_path / "parties.csv").write_text(
        "compiledRelease/id,compiledRelease/parties/0/id,"
        "compiledRelease/parties/0/name\n"
        "rel-1,party-1,NA\n"
        "rel-1,party-2,NULL\n",
        encoding="utf-8",
    )
    mapping = {
        "filename": "parties.csv",
        "table": "parties",
        "pk": ["release_id", "party_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/parties/0/id": "party_id",
            "compiledRelease/parties/0/name": "name",
        },
    }
    db = MagicMock()
    db.check_file_processed.return_value = False
    etl = ETLService(db)

    etl.process_mapping(tmp_path, mapping)

    calls = _upsert_calls_for(db, "parties")
    assert len(calls) == 1
    assert list(calls[0].args[1]["name"]) == ["NA", "NULL"]


def test_process_mapping_hace_rollback_antes_de_registrar_el_fallo(tmp_path):
    """El rollback va antes de registrar FAILED."""
    (tmp_path / "parties.csv").write_text(
        "compiledRelease/id,compiledRelease/parties/0/id\nrel-1,party-1\n",
        encoding="utf-8",
    )
    mapping = {
        "filename": "parties.csv",
        "table": "parties",
        "pk": ["release_id", "party_id"],
        "columns": {
            "compiledRelease/id": "release_id",
            "compiledRelease/parties/0/id": "party_id",
        },
    }
    db = MagicMock()
    db.check_file_processed.return_value = False
    db.bulk_upsert.side_effect = RuntimeError("violación de FK")
    orden = []
    db.conn.rollback.side_effect = lambda: orden.append("rollback")
    db.mark_file_processed.side_effect = lambda *a: orden.append(a[3])

    with pytest.raises(RuntimeError, match="violación de FK"):
        ETLService(db).process_mapping(tmp_path, mapping)

    assert orden == ["rollback", "FAILED"]


def test_process_mapping_registra_el_archivo_con_su_anio(tmp_path):
    """records.csv de 2023 y de 2024 no deben pisarse en etl_runs."""
    carpeta = tmp_path / "2024"
    carpeta.mkdir()
    (carpeta / "records.csv").write_text(
        "compiledRelease/id,compiledRelease/ocid\nrel-1,ocds-1\n", encoding="utf-8"
    )
    mapping = {
        "filename": "records.csv",
        "table": "releases",
        "pk": ["release_id"],
        "columns": {"compiledRelease/id": "release_id", "compiledRelease/ocid": "ocid"},
    }
    db = MagicMock()
    db.check_file_processed.return_value = False

    ETLService(db).process_mapping(carpeta, mapping)

    assert db.check_file_processed.call_args.args[0] == "2024/records.csv"
    assert db.mark_file_processed.call_args.args[:2] == ("2024/records.csv", "releases")
    releases = _upsert_calls_for(db, "releases")[0].args[1]
    assert list(releases["source_file"]) == ["2024/records.csv"]
