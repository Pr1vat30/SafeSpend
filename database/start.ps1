# Starts local Windows PostgreSQL service and applies database/schema.sql
# Usage in PowerShell:
#   .\database\start.ps1

[CmdletBinding()]
param (
    [string]$DbName = $env:PGDATABASE
)

if (-not $DbName) {
    $DbName = "safespend"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$schemaPath = Join-Path $scriptDir "schema.sql"

Write-Host "Configuring PostgreSQL for SafeSpend on Windows..." -ForegroundColor Cyan

# 1. Check if a local PostgreSQL Windows service is installed
$pgServices = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgServices) {
    foreach ($svc in $pgServices) {
        if ($svc.Status -ne "Running") {
            Write-Host "Starting Windows service '$($svc.Name)'..."
            try {
                Start-Service $svc.Name
            } catch {
                Write-Warning "Could not start service $($svc.Name). Make sure you have administrator privileges if required."
            }
        } else {
            Write-Host "PostgreSQL service '$($svc.Name)' is already running." -ForegroundColor Green
        }
    }
} else {
    Write-Host "No Windows PostgreSQL service detected. If using Docker, run: docker compose up -d db" -ForegroundColor Yellow
}

# 2. Check if psql is available in PATH
if (Get-Command psql -ErrorAction SilentlyContinue) {
    Write-Host "Checking if database '$DbName' exists..."
    $dbExists = psql -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DbName'" 2>$null
    if ($dbExists -notmatch "1") {
        Write-Host "Creating database '$DbName'..."
        createdb -U postgres "$DbName"
    }

    Write-Host "Applying schema from $schemaPath..."
    psql -U postgres -v ON_ERROR_STOP=1 -d "$DbName" -f "$schemaPath"
    Write-Host "Ready: postgresql://localhost:5432/$DbName" -ForegroundColor Green
} else {
    Write-Host "psql not found in PATH." -ForegroundColor Yellow
    Write-Host "Running Python database initialization instead..." -ForegroundColor Cyan
    Set-Location (Join-Path $scriptDir "..\backend")
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv run python -m app.core.init_db
    } else {
        python -m app.core.init_db
    }
}
