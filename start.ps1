$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$VirtualEnvironmentPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $VirtualEnvironmentPython) {
    $PythonCommand = $VirtualEnvironmentPython
    $PythonArguments = @()
}
else {
    $PythonCommand = "py"
    $PythonArguments = @("-3.11")
}

Write-Host "EmotiWeave | Preflight checks" -ForegroundColor DarkBlue
& $PythonCommand @PythonArguments scripts\preflight.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Preflight checks failed. Resolve the failed items above." -ForegroundColor DarkRed
    exit $LASTEXITCODE
}

Write-Host "Starting http://127.0.0.1:7860/" -ForegroundColor DarkGreen
& $PythonCommand @PythonArguments main.py
