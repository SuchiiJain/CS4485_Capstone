param(
    [string]$Port = "8010",
    [string]$Token = "",
    [string]$DbPath = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCmd) {
        $pythonExe = $pythonCmd.Path
    } else {
        Write-Error "No Python interpreter found. Create .venv or install Python and add it to PATH."
    }
}

$env:DOCROT_API_PORT = $Port
$env:DOCROT_API_TOKEN = $Token

if ($DbPath -ne "") {
    $env:DOCROT_DB_PATH = $DbPath
}

Write-Host "Starting Docrot API on port $($env:DOCROT_API_PORT)..."
Push-Location $repoRoot
try {
    & $pythonExe -m src.api_server
} finally {
    Pop-Location
}
