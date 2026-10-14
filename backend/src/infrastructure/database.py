import logging
from datetime import datetime
from typing import List, Optional
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from textwrap import dedent

logger = logging.getLogger(__name__)


class DatabaseRepository:
    def __init__(
        self, dsn: str, connect_timeout: int = 10, statement_timeout_ms: int = 60_000
    ):
        self.dsn = dsn
        self.connect_timeout = connect_timeout
        self.statement_timeout_ms = statement_timeout_ms
        self.conn = self._connect()

    def _connect(self):
        conn = psycopg2.connect(
            self.dsn,
            connect_timeout=self.connect_timeout,
            # detectan una conexión "zombie" (p. ej. tras que el SO se
            # duerma) en segundos en vez de colgarse en un recv() sin fin
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=3,
        )
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = {self.statement_timeout_ms}")
        conn.commit()
        return conn

    def check_file_processed(
        self, filename: str, table_name: str, file_hash: str
    ) -> bool:
        """Verifica si un archivo idéntico ya fue procesado PARA ESA TABLA EN PARTICULAR."""
        with self.conn.cursor() as cur:
            cur.execute(
                dedent("""\
                SELECT 
                    1 
                FROM etl_runs 
                WHERE 
                    file_name = %s 
                    AND table_name = %s 
                    AND file_hash = %s 
                    AND status = 'SUCCESS'
                """),
                (filename, table_name, file_hash),
            )
            return cur.fetchone() is not None

    def mark_file_processed(
        self, filename: str, table_name: str, file_hash: str, status: str
    ):
        """Registra la auditoría del archivo procesado (UPSERT)."""
        with self.conn.cursor() as cur:
            cur.execute(
                dedent("""\
                    INSERT INTO etl_runs (file_name, table_name, file_hash, status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (file_name, table_name) DO UPDATE 
                    SET file_hash = EXCLUDED.file_hash, status = EXCLUDED.status, processed_at = NOW();
                """),
                (filename, table_name, file_hash, status),
            )
        self.conn.commit()

    def bulk_upsert(
        self,
        table: str,
        dataframe: pd.DataFrame,
        pk_columns: List[str],
        commit: bool = True,
    ):
        """
        UPSERT masivo en PostgreSQL.
        Usa execute_values para enviar multiples filas de una vez.
        """
        if dataframe.empty:
            return

        # Convertimos NaN y cadenas vacías a None para insertar como NULL
        # ('' rompe columnas NUMERIC: "invalid input syntax for type numeric")
        df = dataframe.replace({pd.NA: None, float("nan"): None, "": None})

        columns = list(df.columns)
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]

        cols_str = ",".join(columns)
        pks_str = ",".join(pk_columns)

        # "col1 = EXCLUDED.col1, col2 = EXCLUDED.col2"
        update_set = ", ".join(
            [f"{col} = EXCLUDED.{col}" for col in columns if col not in pk_columns]
        )

        if update_set:
            conflict_action = f"DO UPDATE SET {update_set}"
        else:
            conflict_action = "DO NOTHING"

        query = dedent(f"""\
            INSERT INTO {table} ({cols_str})
            VALUES %s
            ON CONFLICT ({pks_str}) {conflict_action}
        """)

        with self.conn.cursor() as cur:
            execute_values(cur, query, values, page_size=2000)
        if commit:
            self.conn.commit()

    def start_sync_run(self) -> int:
        """Insercion en sync_log y devuelve el id."""
        with self.conn.cursor() as cur:
            cur.execute(dedent("""\
                INSERT INTO sync_log 
                (status) VALUES ('running') 
                RETURNING id"""))
            run_id = cur.fetchone()[0]
        self.conn.commit()
        return run_id

    def finish_sync_run(
        self,
        run_id: int,
        status: str,
        records_processed: int,
        last_release_date: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ):
        """Finaliza el sync log con resultados generados"""
        with self.conn.cursor() as cur:
            cur.execute(
                dedent("""\
                UPDATE sync_log
                SET finished_at = NOW(),
                    status = %s,
                    records_processed = %s,
                    last_release_date = %s,
                    error_message = %s
                WHERE id = %s
                """),
                (status, records_processed, last_release_date, error_message, run_id),
            )
        self.conn.commit()

    def reconcile_stale_runs(self) -> int:
        """Actualizamos a failed, ya que el scheduler va iniciar el proceso
        y registros con runing son procesos huerfanos fallidos."""
        with self.conn.cursor() as cur:
            cur.execute(dedent("""\
                UPDATE sync_log
                SET status = 'failed',
                    finished_at = NOW(),
                    error_message = 'Interrumpido: el proceso anterior se interrumpió sin cerrar esta ejecución.'
                WHERE status = 'running'
                RETURNING id
                """))
            affected = cur.fetchall()
        self.conn.commit()
        if affected:
            logger.warning(
                f"{len(affected)} ejecución(es) huérfana(s) marcadas como failed: {[r[0] for r in affected]}"
            )
        return len(affected)

    def update_sync_progress(
        self, run_id: int, last_release_date, records_processed: int
    ):
        """Actualizar progreso de una actualizacion en curso"""
        with self.conn.cursor() as cur:
            cur.execute(
                dedent("""\
                UPDATE sync_log
                SET last_release_date = COALESCE(%s, last_release_date),
                    records_processed = %s
                WHERE id = %s
                """),
                (last_release_date, records_processed, run_id),
            )
        self.conn.commit()

    def get_checkpoint_date(self) -> Optional[datetime]:
        """Tomamos la ultima fecha de sync_log"""
        with self.conn.cursor() as cur:
            cur.execute(dedent("""\
                SELECT MAX(last_release_date) FROM sync_log
                WHERE status IN ('success', 'failed') AND last_release_date IS NOT NULL
                """))
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    def get_max_release_date(self) -> Optional[datetime]:
        """Devuelve la máxima fecha de la tabla releases o None."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT MAX(date) FROM releases")
            row = cur.fetchone()
            return row[0] if row and row[0] else None

    # mismo orden que latest_releases: fecha, despues la version de la API
    _RANK_SQL = (
        "SELECT release_id FROM (SELECT release_id,"
        " ROW_NUMBER() OVER (PARTITION BY ocid"
        " ORDER BY date DESC NULLS LAST,"
        " COALESCE(source_file = 'api_sync', false) DESC,"
        " release_id DESC) rn"
        " FROM releases {filtro}) t WHERE t.rn > %s"
    )

    def prune_old_releases(self, ocids: list, keep: int = 1) -> int:
        """Deja las `keep` versiones mas nuevas de cada ocid indicado.

        Los hijos (parties, contracts, contract_documents, ...) se van en
        cascada (ON DELETE CASCADE). Devuelve los releases borrados.
        """
        if not ocids or keep < 1:
            return 0
        sql = self._RANK_SQL.format(filtro="WHERE ocid = ANY(%s)")
        return self._delete_releases(sql, (list(ocids), keep))

    def prune_all_old_releases(self, keep: int = 1) -> int:
        """Igual que prune_old_releases pero sobre todo el corpus.

        Se usa al terminar la carga historica (CSV) y en mantenimiento: la
        base guarda el estado actual (1 version por ocid), no el historial.
        """
        if keep < 1:
            return 0
        sql = self._RANK_SQL.format(filtro="")
        return self._delete_releases(sql, (keep,))

    def delete_other_versions(self, ocid: str, keep_release_id: str) -> int:
        """Borra las otras versiones de un ocid y deja solo keep_release_id."""
        sql = "SELECT release_id FROM releases WHERE ocid = %s AND release_id <> %s"
        return self._delete_releases(sql, (ocid, keep_release_id))

    def _delete_releases(self, subquery: str, params: tuple) -> int:
        """Ejecuta el DELETE de releases antiguos y commitea."""
        sql = f"DELETE FROM releases WHERE release_id IN ({subquery})"
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            borrados = cur.rowcount
        self.conn.commit()
        if borrados:
            logger.info(f"Retencion: {borrados} releases antiguos borrados")
        return borrados

    def is_alive(self) -> bool:
        """Detecta conexion activa."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def reconnect_if_closed(self):
        """Reconecta si la conexion esta cerrada no esta viva"""
        if self.conn.closed or not self.is_alive():
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = self._connect()

    def refresh_materialized_view(self, view_name: str):
        """Para refrescar vistas materializada, no puede ser con transacción.
        Se desactiva el statment_timeout durante el refresh porque puede demorar mucho."""
        self.conn.commit()  # asegurar que todo lo pendiente esté commiteado
        self.conn.autocommit = True
        try:
            with self.conn.cursor() as cur:
                cur.execute("SET statement_timeout = 0")
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name};")
        finally:
            try:
                with self.conn.cursor() as cur:
                    cur.execute(f"SET statement_timeout = {self.statement_timeout_ms}")
            finally:
                self.conn.autocommit = False

    def close(self):
        self.conn.close()
