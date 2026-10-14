from datetime import datetime
from textwrap import dedent
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest

from src.infrastructure.database import DatabaseRepository


@pytest.fixture
def mock_conn():
    """Fixture que simula psycopg2.connect y su cursor"""
    with patch("src.infrastructure.database.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        mock_connect.return_value = conn
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        yield conn, cursor


def _make_repo(mock_conn):
    """Construye el repo y resetea los mocks"""
    conn, cursor = mock_conn
    repo = DatabaseRepository("dummy_dsn")
    cursor.execute.reset_mock()
    conn.commit.reset_mock()
    return repo, conn, cursor


def test_start_sync_run(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)
    cursor.fetchone.return_value = [42]

    run_id = repo.start_sync_run()

    assert run_id == 42
    cursor.execute.assert_called_once_with(dedent("""\
                INSERT INTO sync_log 
                (status) VALUES ('running') 
                RETURNING id"""))
    conn.commit.assert_called_once()


def test_finish_sync_run(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)
    now = datetime(2025, 1, 1, 12, 0, 0)

    repo.finish_sync_run(
        run_id=1,
        status="success",
        records_processed=10,
        last_release_date=now,
        error_message=None,
    )

    expected_sql = dedent("""\
        UPDATE sync_log
        SET finished_at = NOW(),
            status = %s,
            records_processed = %s,
            last_release_date = %s,
            error_message = %s
        WHERE id = %s
    """)
    cursor.execute.assert_called_once_with(
        expected_sql,
        ("success", 10, now, None, 1),
    )
    conn.commit.assert_called_once()


def test_get_checkpoint_date_returns_date(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)
    expected_date = datetime(2025, 5, 1)
    cursor.fetchone.return_value = [expected_date]

    result = repo.get_checkpoint_date()

    assert result == expected_date
    cursor.execute.assert_called_once_with(dedent("""\
        SELECT MAX(last_release_date) FROM sync_log
        WHERE status IN ('success', 'failed') AND last_release_date IS NOT NULL
    """))


def test_get_checkpoint_date_returns_none(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)
    cursor.fetchone.return_value = None

    result = repo.get_checkpoint_date()

    assert result is None
    cursor.execute.assert_called_once_with(dedent("""\
        SELECT MAX(last_release_date) FROM sync_log
        WHERE status IN ('success', 'failed') AND last_release_date IS NOT NULL
    """))


def test_update_sync_progress(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)
    now = datetime(2025, 5, 1)

    repo.update_sync_progress(run_id=7, last_release_date=now, records_processed=33)

    cursor.execute.assert_called_once_with(
        dedent("""\
            UPDATE sync_log
            SET last_release_date = COALESCE(%s, last_release_date),
                records_processed = %s
            WHERE id = %s
        """),
        (now, 33, 7),
    )
    conn.commit.assert_called_once()


def test_reconcile_stale_runs(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)
    cursor.fetchall.return_value = [(3,), (4,)]

    affected = repo.reconcile_stale_runs()

    assert affected == 2
    cursor.execute.assert_called_once_with(dedent("""\
        UPDATE sync_log
        SET status = 'failed',
            finished_at = NOW(),
            error_message = 'Interrumpido: el proceso anterior se interrumpió sin cerrar esta ejecución.'
        WHERE status = 'running'
        RETURNING id
    """))
    conn.commit.assert_called_once()


def test_is_alive_true(mock_conn):
    conn, cursor = mock_conn
    repo = DatabaseRepository("dummy_dsn")

    assert repo.is_alive() is True


def test_is_alive_false_on_error(mock_conn):
    conn, cursor = mock_conn
    cursor.execute.side_effect = Exception("boom")
    repo = DatabaseRepository.__new__(DatabaseRepository)
    repo.conn = conn

    assert repo.is_alive() is False


def test_reconnect_if_closed_reconnects():
    with patch("src.infrastructure.database.psycopg2.connect") as mock_connect:
        old_conn = MagicMock()
        old_conn.closed = 1  # psycopg2 usa 1 para conexión cerrada
        new_conn = MagicMock()
        mock_connect.return_value = new_conn

        repo = DatabaseRepository.__new__(DatabaseRepository)
        repo.dsn = "dummy_dsn"
        repo.connect_timeout = 10
        repo.statement_timeout_ms = 60_000
        repo.conn = old_conn

        repo.reconnect_if_closed()

        mock_connect.assert_called_once()
        assert mock_connect.call_args.args[0] == "dummy_dsn"
        assert repo.conn is new_conn
        assert new_conn.autocommit is False


def test_reconnect_if_closed_when_open():
    with patch("src.infrastructure.database.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        conn.closed = 0  # conexión abierta

        repo = DatabaseRepository.__new__(DatabaseRepository)
        repo.dsn = "dummy_dsn"
        repo.conn = conn

        repo.reconnect_if_closed()

        mock_connect.assert_not_called()
        assert repo.conn is conn


def test_reconnect_when_zombie():
    """Reconecta si is_alive() falla aunque .closed sea False"""
    with patch("src.infrastructure.database.psycopg2.connect") as mock_connect:
        old_conn = MagicMock()
        old_conn.closed = 0
        old_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("zombie")

        new_conn = MagicMock()
        mock_connect.return_value = new_conn

        repo = DatabaseRepository.__new__(DatabaseRepository)
        repo.dsn = "dummy_dsn"
        repo.connect_timeout = 10
        repo.statement_timeout_ms = 60_000
        repo.conn = old_conn

        repo.reconnect_if_closed()

        mock_connect.assert_called_once()
        assert repo.conn is new_conn


def test_refresh_materialized_view(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)

    repo.refresh_materialized_view("party_master")

    assert cursor.execute.call_args_list == [
        call("SET statement_timeout = 0"),
        call("REFRESH MATERIALIZED VIEW CONCURRENTLY party_master;"),
        call("SET statement_timeout = 60000"),
    ]
    assert conn.autocommit is False


def test_refresh_materialized_view_restores_autocommit_on_error(mock_conn):
    conn, cursor = mock_conn
    repo = DatabaseRepository("dummy_dsn")
    cursor.execute.reset_mock()

    def fail_on_refresh(sql):
        if "REFRESH" in sql:
            raise RuntimeError("boom")

    cursor.execute.side_effect = fail_on_refresh

    with pytest.raises(RuntimeError):
        repo.refresh_materialized_view("party_master")

    assert conn.autocommit is False


def test_bulk_upsert_converts_empty_strings_to_none(mock_conn):
    conn, cursor = mock_conn
    repo = DatabaseRepository("dummy_dsn")
    df = pd.DataFrame(
        {
            "release_id": ["r1"],
            "value_amount": [""],  # numérico vacío -> None
            "name": [""],  # texto vacío -> None
        }
    )

    with patch("src.infrastructure.database.execute_values") as mock_exec:
        repo.bulk_upsert("tender", df, ["release_id"])

    values = mock_exec.call_args.args[2]  # execute_values(cur, query, values, ...)
    assert values == [("r1", None, None)]


def test_bulk_upsert_commit_false_does_not_commit(mock_conn):
    conn, cursor = mock_conn
    repo = DatabaseRepository("dummy_dsn")
    conn.commit.reset_mock()
    df = pd.DataFrame({"release_id": ["r1"], "name": ["x"]})

    with patch("src.infrastructure.database.execute_values"):
        repo.bulk_upsert("tender", df, ["release_id"], commit=False)

    conn.commit.assert_not_called()



def test_delete_other_versions_conserva_solo_la_indicada(mock_conn):
    repo, conn, cursor = _make_repo(mock_conn)
    cursor.rowcount = 1

    borrados = repo.delete_other_versions("ocds-1", "rel-nueva")

    sql, params = cursor.execute.call_args.args
    assert sql.startswith("DELETE FROM releases WHERE release_id IN (")
    assert "ocid = %s AND release_id <> %s" in sql
    assert params == ("ocds-1", "rel-nueva")
    assert borrados == 1


def test_retencion_a_igual_fecha_prefiere_la_version_de_la_api():
    """Orden: fecha, luego la versión de la API, luego release_id."""
    orden = DatabaseRepository._RANK_SQL
    assert orden.index("date DESC NULLS LAST") < orden.index("source_file = 'api_sync'")
    assert orden.index("source_file = 'api_sync'") < orden.index("release_id DESC")
