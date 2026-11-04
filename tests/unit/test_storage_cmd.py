import csv
import io
import json
import os
import subprocess
from pathlib import Path

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


def test_hardlink_provenance_is_visible_and_escaped_in_all_reports(
    tmp_path, monkeypatch
):
    from fixos.diagnostics import large_files
    from fixos.diagnostics.storage_rules import decide_file

    # Avoid making the Wellman temp directory's protected ancestors test inputs.
    monkeypatch.setattr(
        large_files,
        "decide_file",
        lambda row: decide_file(
            {
                **row,
                "path": str(Path("/fixture") / Path(row["path"]).relative_to(tmp_path)),
            }
        ),
    )
    cache = tmp_path / ".cache/item.bin"
    cache.parent.mkdir()
    cache.write_bytes(b"x" * 20)
    alias = tmp_path / "backups/<svg onload=alert(1)>.bin"
    alias.parent.mkdir()
    os.link(cache, alias)
    args = [str(cache.parent), str(alias.parent), "--min-mb", "0", "--max-seconds", "1"]
    runner = CliRunner()
    table = runner.invoke(storage, args)
    assert table.exit_code == 0, table.output
    assert str(cache) in table.output and str(alias) in table.output
    assert "Ścieżka decyzji: " + str(alias) in table.output
    assert "Obserwacja UTC:" in table.output
    assert "znane ścieżki: 2/2" in table.output
    page = runner.invoke(storage, args + ["--format", "html"])
    assert page.exit_code == 0, page.output
    assert "<svg onload=alert(1)>" not in page.output
    assert "&lt;svg onload=alert(1)&gt;" in page.output
    csv_result = runner.invoke(storage, args + ["--format", "csv"])
    assert csv_result.exit_code == 0, csv_result.output
    rows = list(csv.DictReader(io.StringIO(csv_result.output)))
    assert len(rows) == 1
    assert rows[0]["decision_path"] == str(alias)
    assert set(json.loads(rows[0]["observed_paths"])) == {str(cache), str(alias)}
    assert rows[0]["observed_at"]
    assert rows[0]["observed_paths_may_be_incomplete"] == "False"
