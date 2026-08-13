from __future__ import annotations

import os
import shutil
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


def test_start_script_prefers_project_virtual_environment(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    shutil.copy2(project_root / "start.ps1", tmp_path / "start.ps1")

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "preflight.py").write_text("PREFLIGHT_FROM_VENV\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("MAIN_FROM_VENV\n", encoding="utf-8")

    venv_scripts = tmp_path / ".venv" / "Scripts"
    venv_scripts.mkdir(parents=True)
    more_command = shutil.which("more.com")
    assert more_command is not None
    shutil.copy2(more_command, venv_scripts / "python.exe")

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    (fake_bin / "py.cmd").write_text("@echo SYSTEM_LAUNCHER_USED\r\n", encoding="utf-8")
    environment = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(tmp_path / "start.ps1"),
        ],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=environment,
    )

    output = (result.stdout + result.stderr).decode(errors="replace")
    assert result.returncode == 0, output
    assert "PREFLIGHT_FROM_VENV" in output
    assert "MAIN_FROM_VENV" in output
    assert "SYSTEM_LAUNCHER_USED" not in output
