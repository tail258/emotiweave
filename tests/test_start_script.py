from __future__ import annotations

import subprocess
from pathlib import Path


def test_start_script_parses_in_windows_powershell_51() -> None:
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "start.ps1"
    command = (
        f"$content = Get-Content -Raw -LiteralPath '{script_path}'; "
        "[scriptblock]::Create($content) | Out-Null"
    )

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        check=False,
    )

    output = (result.stdout + result.stderr).decode(errors="replace")
    assert result.returncode == 0, output
