# scripts/run_portal.ps1 — Somalia + Ogaden cross-border GIS portal (single process)
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\run_portal.ps1
# Starts uvicorn and opens the default browser at http://localhost:8000/dashboard automatically.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# 1. Virtual environment (created once)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
    python -m venv .venv
}
$venvPython = (Resolve-Path ".venv\Scripts\python.exe").Path

# 2. Dependencies (installed on first run, or whenever requirements.txt changes)
$marker = ".venv\.deps-installed"
if (-not (Test-Path $marker) -or ((Get-Item requirements.txt).LastWriteTime -gt (Get-Item $marker).LastWriteTime)) {
    Write-Host "Installing requirements..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
    if (Test-Path $marker) { (Get-Item $marker).LastWriteTime = Get-Date } else { New-Item -ItemType File $marker | Out-Null }
}

# 3. Serve — the spec run command (no static server; proxies + dashboard in one process).
#    Postgres is optional: if unreachable, DB-backed endpoints degrade and the GIS portal serves anyway.
$dashboardUrl = "http://localhost:8000/dashboard"

# 4. Auto-open the default browser the moment the portal answers (background watcher)
$browserJob = Start-Job -Name OpenDashboard -ScriptBlock {
    param($url)
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    Start-Process $url   # opens the default browser
} -ArgumentList $dashboardUrl

Write-Host ""
Write-Host "Portal starting -> $dashboardUrl   (browser opens automatically; Ctrl+C to stop)" -ForegroundColor Green
Write-Host ""
try {
    & $venvPython -m uvicorn main:app --reload --port 8000
} finally {
    Remove-Job -Job $browserJob -Force -ErrorAction SilentlyContinue
}
