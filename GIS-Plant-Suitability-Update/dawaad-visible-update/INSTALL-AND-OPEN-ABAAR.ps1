$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageWeb = Join-Path $PackageRoot "web"
$TargetRoot = "C:\Users\EastG\agri-lab-dashboard"
$Port = 8765

if (-not (Test-Path $PackageWeb)) {
    throw "Package web folder missing. Extract the complete ZIP first."
}
if (-not (Test-Path $TargetRoot)) {
    New-Item -ItemType Directory -Path $TargetRoot -Force | Out-Null
}

$Targets = @()
if (Test-Path "$TargetRoot\web") { $Targets += "$TargetRoot\web" }
if (Test-Path "$TargetRoot\app\web") { $Targets += "$TargetRoot\app\web" }
if ($Targets.Count -eq 0) {
    New-Item -ItemType Directory -Path "$TargetRoot\web" -Force | Out-Null
    $Targets += "$TargetRoot\web"
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
foreach ($TargetWeb in $Targets) {
    foreach ($Name in @("dashboard.html", "agri.i18n.js", "agri.shared.js", "agri.store.js", "dawaad.html", "dawaad-map.js", "dawaad-map.css", "drought.mock.json", "pastoral-tools.js", "dawaad.aquifers.geojson")) {
        $Existing = Join-Path $TargetWeb $Name
        if (Test-Path $Existing) { Copy-Item $Existing "$Existing.backup-$Stamp" -Force }
    }
    Copy-Item (Join-Path $PackageWeb "*") $TargetWeb -Recurse -Force
    Write-Host "Updated: $TargetWeb" -ForegroundColor Green
}

if (Test-Path "$TargetRoot\web\dawaad.html") {
    $ServeRoot = $TargetRoot
} elseif (Test-Path "$TargetRoot\app\web\dawaad.html") {
    $ServeRoot = "$TargetRoot\app"
} else {
    throw "dawaad.html was not installed."
}

$Dashboard = Join-Path $ServeRoot "web\dashboard.html"
$Dawaad = Join-Path $ServeRoot "web\dawaad.html"
$Mock = Join-Path $ServeRoot "web\drought.mock.json"
$Tools = Join-Path $ServeRoot "web\pastoral-tools.js"
$Aquifers = Join-Path $ServeRoot "web\dawaad.aquifers.geojson"
if (-not (Select-String -Path $Dashboard -Pattern "plant-suitability-card" -Quiet)) {
    throw "The polygon Plant Selector suitability workflow is missing."
}
if (-not (Select-String -Path $Dawaad -Pattern "Drought Monitoring / Kormeerka Abaaraha" -Quiet)) {
    throw "The visible drought monitoring panel is missing."
}
if (-not (Select-String -Path $Dawaad -Pattern "Pastoral Utility Tools" -Quiet)) {
    throw "The pastoral utility panel is missing."
}
if (-not (Test-Path $Mock)) { throw "drought.mock.json is missing." }
if (-not (Test-Path $Tools)) { throw "pastoral-tools.js is missing." }
if (-not (Test-Path $Aquifers)) { throw "dawaad.aquifers.geojson is missing." }

try {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { if ($_ -and $_ -ne $PID) { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
} catch {}

$Python = Get-Command py.exe -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command python.exe -ErrorAction SilentlyContinue }
if (-not $Python) { throw "Python was not found." }

$Server = Start-Process -FilePath $Python.Source `
    -ArgumentList @("-m", "http.server", "$Port", "--bind", "127.0.0.1") `
    -WorkingDirectory $ServeRoot -PassThru

$Url = "http://127.0.0.1:$Port/web/dashboard.html?build=d4fa740-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$Ready = $false
for ($Attempt = 1; $Attempt -le 12; $Attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $Response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
        if ($Response.StatusCode -eq 200 -and $Response.Content -match "Plant Selector") {
            $Ready = $true
            break
        }
    } catch {}
}
if (-not $Ready) {
    Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue
    throw "The fresh web server did not start correctly."
}

Write-Host ""
Write-Host "GIS polygon Plant Selector and Dawaad tools are installed and verified." -ForegroundColor Green
Write-Host "Draw or click a Beer polygon, then select a plant to see Green, Yellow or Red suitability." -ForegroundColor Cyan
Write-Host "Opening: $Url" -ForegroundColor Cyan
Start-Process $Url
