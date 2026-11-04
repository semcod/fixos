import csv
import io
import json
import subprocess

from click.testing import CliRunner

from fixos.cli.storage_cmd import _cell, storage


def test_cli_works_without_llm_config_network_or_subprocess(tmp_path, monkeypatch):
    from fixos.cli.main import cli
    from fixos.config import FixOsConfig

    def forbidden(*args, **kwargs):
        raise AssertionError("LLM configuration/network/commands are not needed")

    monkeypatch.setattr(FixOsConfig, "load", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    path = tmp_path / "large.zip"
    path.write_bytes(b"PK\x03\x04" + b"x" * 20)
    before = path.read_bytes()
    result = CliRunner().invoke(
        cli, ["storage", str(tmp_path), "--min-mb", "0", "--json", "--max-seconds", "1"]
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["llm_used"] is False and report["data_mutations"] == 0
    assert report["files"][0]["path"] == str(path)
    assert path.read_bytes() == before


def test_reports_escape_names_and_expose_scan_coverage(tmp_path):
    path = tmp_path / '<img src=x onerror="alert(1)">.zip'
    path.write_bytes(b"x" * 20)
    runner = CliRunner()
    html_result = runner.invoke(
        storage,
        [str(tmp_path), "--min-mb", "0", "--format", "html", "--max-seconds", "1"],
    )
    assert html_result.exit_code == 0, html_result.output
    assert "<img src=x onerror=" not in html_result.output
    assert "&lt;img src=x onerror=" in html_result.output
    assert "Skan:" in html_result.output
    assert 'id="query"' in html_result.output and 'id="decision"' in html_result.output
    assert "authorizedDelete:false" in html_result.output
    assert "Brak dużych plików" not in html_result.output
    csv_result = runner.invoke(
        storage,
        [str(tmp_path), "--min-mb", "0", "--format", "csv", "--max-seconds", "1"],
    )
    rows = list(csv.DictReader(io.StringIO(csv_result.output)))
    assert rows[0]["path"] == str(path)
    assert rows[0]["scan_status"] == "complete"


def test_export_never_overwrites_existing_file(tmp_path):
    target = tmp_path / "report.json"
    target.write_text("keep")
    result = CliRunner().invoke(
        storage,
        [str(tmp_path), "--output", str(target), "--json", "--max-seconds", "1"],
    )
    assert result.exit_code != 0
    assert target.read_text() == "keep"


def test_csv_formula_cells_are_neutralized():
    for value in ["=HYPERLINK('x')", "+SUM(1,2)", "@x", "-1", "\tcmd"]:
        assert _cell(value).startswith("'")


def test_incomplete_scan_is_explicit_in_human_output(tmp_path):
    for index in range(4):
        (tmp_path / f"{index}.bin").write_bytes(b"x")
    result = CliRunner().invoke(
        storage, [str(tmp_path), "--min-mb", "0", "--max-entries", "1"]
    )
    assert result.exit_code == 0, result.output
    assert "Skan: partial" in result.output
    assert "Budżet wyczerpany: True" in result.output
