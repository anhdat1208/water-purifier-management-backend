# Chạy từ thư mục backend, sau khi Postgres đã chạy:
#   .\scripts\setup-postgres.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Find-ComposeRoot([string]$StartPath) {
    $current = $StartPath
    while ($current) {
        if (Test-Path (Join-Path $current "docker-compose.yml")) {
            return $current
        }
        $parent = Split-Path $current -Parent
        if (-not $parent -or $parent -eq $current) { break }
        $current = $parent
    }
    return $null
}

$ComposeRoot = Find-ComposeRoot $Root
if (-not $ComposeRoot) {
    throw "Khong tim thay docker-compose.yml. Chay tu monorepo water-purifier-manager."
}

Write-Host "==> Khoi dong Postgres + Redis (Docker)..." -ForegroundColor Cyan
Set-Location $ComposeRoot
docker compose up -d postgres redis

Write-Host "==> Doi Postgres san sang..." -ForegroundColor Cyan
$retries = 30
for ($i = 1; $i -le $retries; $i++) {
    docker compose exec -T postgres pg_isready -U waterpurifier -d waterpurifier 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Postgres ready." -ForegroundColor Green
        break
    }
    if ($i -eq $retries) { throw "Postgres khong san sang sau $retries lan thu." }
    Start-Sleep -Seconds 2
}

Set-Location $Root

Write-Host "==> Cai dependencies..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt -q

Write-Host "==> Chay migration (tao bang)..." -ForegroundColor Cyan
.\venv\Scripts\alembic.exe upgrade head

Write-Host ""
Write-Host "Xong! Chay API:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
Write-Host ""
Write-Host "Database: postgresql://waterpurifier:waterpurifier@localhost:5432/waterpurifier"
