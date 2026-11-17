"""CLI input validation and report exit status."""
from leadflow_bridge.cli import main


def test_cli_does_not_run_without_explicit_environment_token(monkeypatch, capsys):
    monkeypatch.delenv("LEADFLOW_API_TOKEN", raising=False)
    code = main(["sync", "examples/leads.csv"])
    assert code == 2
    assert "LEADFLOW_API_TOKEN" in capsys.readouterr().err


def test_cli_fails_on_missing_csv_without_leaking_token(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LEADFLOW_API_TOKEN", "secret-never-print")
    code = main(["sync", str(tmp_path / "missing.csv")])
    assert code == 2
    assert "secret-never-print" not in capsys.readouterr().err
