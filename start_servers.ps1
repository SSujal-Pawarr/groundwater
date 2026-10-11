$ErrorActionPreference = "SilentlyContinue"

$ProjectRoot = $PSScriptRoot

# Clean up any previous server instances on ports 8000 and 5173
$p8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($p8000) {
    Write-Host "Releasing port 8000 (PID $p8000)..."
    Stop-Process -Id $p8000 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 600
}

$p5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($p5173) {
    Write-Host "Releasing port 5173 (PID $p5173)..."
    Stop-Process -Id $p5173 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 600
}

Write-Host "Starting FastAPI Backend on port 8000..."
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $ProjectRoot

Write-Host "Starting Vite Frontend on port 5173..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory "$ProjectRoot\frontend"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " Servers are now running!" -ForegroundColor Green
Write-Host " Frontend Web App:  http://localhost:5173" -ForegroundColor Cyan
Write-Host " Backend API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Green

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"
