from unittest.mock import patch

from src.config import settings
from src.etl.flatten_adapter import FLATTEN_TIMEOUT_SECONDS, record_to_dataframes


def _write_fresh_flattened(output_dir):
    out = output_dir / "flattened"
    out.mkdir(exist_ok=True)
    (out / "contracts.csv").write_text(
        "ocid,compiledRelease/id\nocds-new,new-release\n", encoding="utf-8"
    )


def test_record_to_dataframes_cleans_stale_flattened_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "debug_flatten_output", True)
    monkeypatch.setattr(settings, "debug_flatten_dir", str(tmp_path))

    # Simular un flattened/ previo con un CSV stale (de otro record)
    stale_dir = tmp_path / "flattened"
    stale_dir.mkdir(parents=True)
    (stale_dir / "stale_sheet.csv").write_text(
        "ocid,compiledRelease/id\nocds-old,old-release\n", encoding="utf-8"
    )

    with patch("src.etl.flatten_adapter.subprocess.run") as mock_run:
        mock_run.side_effect = lambda *a, **k: _write_fresh_flattened(tmp_path)
        dataframes = record_to_dataframes(
            {"records": [{"ocid": "ocds-new", "compiledRelease": {"id": "new-release"}}]}
        )

    # El subproceso tiene tope de tiempo: no puede colgar el worker un día entero.
    assert mock_run.call_args.kwargs["timeout"] == FLATTEN_TIMEOUT_SECONDS

    # El CSV stale del record anterior NO debe filtrarse en el resultado
    assert "stale_sheet" not in dataframes
    assert "contracts" in dataframes
    assert dataframes["contracts"].iloc[0]["compiledRelease/id"] == "new-release"
