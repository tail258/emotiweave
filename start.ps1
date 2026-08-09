$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "EmotiWeave | Preflight checks" -ForegroundColor DarkBlue
py -3.11 scripts\preflight.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Preflight checks failed. Resolve the failed items above." -ForegroundColor DarkRed
    exit $LASTEXITCODE
}

Write-Host "Starting http://127.0.0.1:7860/" -ForegroundColor DarkGreen
py -3.11 main.py
