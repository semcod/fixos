"""The adopted standard packs keep their managed projection digests current.

CI ``governance / enforce`` runs ``standard_pack_check.py``; the local gate does
not. Running it here makes a manifest edit without a matching
``standard-adoption.json`` update fail in pytest instead of only in CI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_standard_pack_check_reports_no_findings():
    result = subprocess.run(
        [sys.executable, ".governance/standard_pack_check.py", "--root", ".", "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    report = json.loads(result.stdout)
    assert report["findings"] == [], report["findings"]
    assert report["ok"] is True
    assert result.returncode == 0
